"""
New York County Records API Integration
Integrates with New York county clerk and property assessment APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class NewYorkCountyAPI(BaseAPIIntegration):
    """
    Integration with New York County Clerk and Assessment APIs
    Supports NYC boroughs and major upstate counties
    """

    COUNTY_APIS = {
        "new-york": {  # Manhattan
            "base_url": "https://a836-acris.nyc.gov/api",
            "clerk_url": "https://iapps.courts.state.ny.us/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "ucc_filings",
                "liens",
            ],
        },
        "kings": {  # Brooklyn
            "base_url": "https://a836-acris.nyc.gov/api",
            "clerk_url": "https://iapps.courts.state.ny.us/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "liens",
            ],
        },
        "queens": {
            "base_url": "https://a836-acris.nyc.gov/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "bronx": {
            "base_url": "https://a836-acris.nyc.gov/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "richmond": {  # Staten Island
            "base_url": "https://a836-acris.nyc.gov/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "nassau": {
            "base_url": "https://www.nassaucountyny.gov/api/records",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "suffolk": {
            "base_url": "https://www.suffolkcountyny.gov/api/records",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "westchester": {
            "base_url": "https://www.westchestergov.com/api/records",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "erie": {  # Buffalo
            "base_url": "https://www2.erie.gov/api/records",
            "features": ["property_search", "deed_records"],
        },
        "monroe": {  # Rochester
            "base_url": "https://www.monroecounty.gov/api/records",
            "features": ["property_search", "deed_records"],
        },
        "albany": {
            "base_url": "https://www.albanycounty.com/api/records",
            "features": ["property_search", "deed_records"],
        },
        "onondaga": {  # Syracuse
            "base_url": "https://www.ongov.net/api/records",
            "features": ["property_search", "deed_records"],
        },
    }

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        self.county_name = self._extract_county_name(
            config.get("jurisdiction_name", "")
        )
        self.county_config = self.COUNTY_APIS.get(
            self.county_name.lower().replace(" ", "-"), {}
        )

        if self.county_config:
            self.base_url = self.county_config.get("base_url", "")
            self.clerk_url = self.county_config.get("clerk_url", "")
            self.available_features = self.county_config.get("features", [])
        else:
            logger.warning(f"No specific API config for NY county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countyny.gov/api/records"
            )
            self.clerk_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized New York API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()

        # Handle NYC borough names
        borough_mapping = {
            "manhattan": "new-york",
            "brooklyn": "kings",
            "staten island": "richmond",
        }

        for borough, county in borough_mapping.items():
            if borough in name:
                return county

        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with NY API"""
        if self.api_key:
            logger.info("NY API key authentication configured")
            return True
        # NYC ACRIS is publicly accessible
        logger.info("Using public access for NY records")
        return True

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for property and deed records"""
        results = []

        if "property_search" in self.available_features:
            results.extend(self._search_property_records(query))

        if "deed_records" in self.available_features:
            results.extend(self._search_deed_records(query))

        if "mortgage_records" in self.available_features:
            results.extend(self._search_mortgage_records(query))

        return results

    def _search_property_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search property assessment records"""
        try:
            params = {
                "bbl": query.get("bbl", ""),  # Borough-Block-Lot
                "address": query.get("address", ""),
                "owner": query.get("owner_name", ""),
                "borough": query.get("borough", ""),
                "block": query.get("block", ""),
                "lot": query.get("lot", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "properties/search", params=params)
            data = self.validate_response(response)

            properties = data.get("properties", data.get("results", []))
            return [self._map_property_to_standard(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Property search failed for {self.county_name}: {e}")
            return []

    def _search_deed_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search deed records from ACRIS"""
        try:
            params = {
                "party_name": query.get("party_name", ""),
                "doc_type": query.get("doc_type", "DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
                "borough": query.get("borough", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "documents/search", params=params)
            data = self.validate_response(response)

            records = data.get("documents", data.get("records", []))
            return [self._map_deed_to_standard(record) for record in records]

        except Exception as e:
            logger.error(f"Deed search failed for {self.county_name}: {e}")
            return []

    def _search_mortgage_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search mortgage records"""
        try:
            params = {
                "borrower": query.get("borrower", ""),
                "lender": query.get("lender", ""),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
                "min_amount": query.get("min_amount", ""),
                "max_amount": query.get("max_amount", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "mortgages/search", params=params)
            data = self.validate_response(response)

            mortgages = data.get("mortgages", [])
            return [self._map_mortgage_to_standard(m) for m in mortgages]

        except Exception as e:
            logger.error(f"Mortgage search failed for {self.county_name}: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed record information"""
        try:
            response = self.make_request("GET", f"documents/{record_id}")
            data = self.validate_response(response)
            return self._map_deed_to_standard(data)
        except Exception as e:
            logger.error(f"Failed to get details for {record_id}: {e}")
            return {}

    def get_lien_records(self, property_id: str) -> List[Dict[str, Any]]:
        """Get lien records for a property"""
        if "liens" not in self.available_features:
            return []

        try:
            response = self.make_request("GET", f"properties/{property_id}/liens")
            data = self.validate_response(response)

            liens = data.get("liens", [])
            return [self._map_lien_to_standard(lien) for lien in liens]

        except Exception as e:
            logger.error(f"Failed to get liens for {property_id}: {e}")
            return []

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map NY property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("bbl") or data.get("property_id"),
            "title": f"Property - {data.get('address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("market_value", 0)),
            "address": data.get("address", ""),
            "borough": data.get("borough", ""),
            "block": data.get("block", ""),
            "lot": data.get("lot", ""),
            "city": data.get("city", "New York"),
            "state": "NY",
            "zip_code": data.get("zip_code", ""),
            "date": data.get("valuation_date"),
            "description": data.get("building_class_description", ""),
            "raw_data": data,
            "data_source": f"newyork_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map NY deed record to standard format"""
        return {
            "record_type": data.get("doc_type", "deed").lower(),
            "record_id": data.get("document_id") or data.get("crfn"),
            "title": f"{data.get('doc_type', 'Deed')} - {data.get('party1', 'Unknown')}",
            "grantor": data.get("party1", ""),
            "grantee": data.get("party2", ""),
            "amount": float(data.get("doc_amount", 0)),
            "address": data.get("property_address", ""),
            "borough": data.get("borough", ""),
            "city": "New York",
            "state": "NY",
            "date": data.get("recorded_date") or data.get("document_date"),
            "document_number": data.get("crfn") or data.get("document_id"),
            "reel_page": f"{data.get('reel', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"newyork_{self.county_name}_acris",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map mortgage record to standard format"""
        return {
            "record_type": "mortgage",
            "record_id": data.get("document_id") or data.get("crfn"),
            "title": f"Mortgage - {data.get('borrower', 'Unknown')}",
            "grantor": data.get("borrower", ""),
            "grantee": data.get("lender", ""),
            "borrower": data.get("borrower", ""),
            "lender": data.get("lender", ""),
            "amount": float(data.get("loan_amount", 0)),
            "date": data.get("recorded_date"),
            "document_number": data.get("crfn"),
            "mortgage_type": data.get("mortgage_type", ""),
            "raw_data": data,
            "data_source": f"newyork_{self.county_name}_mortgage",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_lien_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map lien record to standard format"""
        return {
            "record_type": "lien",
            "record_id": data.get("lien_id"),
            "title": f"Lien - {data.get('lien_type', 'Unknown')}",
            "grantor": data.get("debtor", ""),
            "grantee": data.get("creditor", ""),
            "amount": float(data.get("lien_amount", 0)),
            "lien_type": data.get("lien_type", ""),
            "date": data.get("filing_date"),
            "status": data.get("status", "active"),
            "raw_data": data,
            "data_source": f"newyork_{self.county_name}_lien",
            "scraped_at": datetime.now().isoformat(),
        }


class NYCACRISApi(NewYorkCountyAPI):
    """Specialized integration for NYC ACRIS (all 5 boroughs)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = config.get("jurisdiction_name", "New York County")
        super().__init__(jurisdiction_id, config)
        self.base_url = "https://a836-acris.nyc.gov/api"

    def search_by_borough_block_lot(
        self, borough: int, block: int, lot: int
    ) -> List[Dict[str, Any]]:
        """Search documents by BBL (Borough-Block-Lot)"""
        try:
            bbl = f"{borough}{str(block).zfill(5)}{str(lot).zfill(4)}"
            response = self.make_request("GET", "documents/bbl", params={"bbl": bbl})
            data = self.validate_response(response)

            documents = data.get("documents", [])
            return [self._map_deed_to_standard(doc) for doc in documents]

        except Exception as e:
            logger.error(f"BBL search failed: {e}")
            return []


class NassauCountyAPI(NewYorkCountyAPI):
    """Specialized integration for Nassau County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Nassau County"
        super().__init__(jurisdiction_id, config)

    def get_tax_grievance_info(self, property_id: str) -> Dict[str, Any]:
        """Get tax grievance information (Nassau specific)"""
        try:
            response = self.make_request("GET", f"properties/{property_id}/grievances")
            data = self.validate_response(response)
            return {
                "grievance_status": data.get("status"),
                "filing_deadline": data.get("filing_deadline"),
                "reduction_history": data.get("reduction_history", []),
            }
        except Exception as e:
            logger.error(f"Failed to get grievance info: {e}")
            return {}


class SuffolkCountyAPI(NewYorkCountyAPI):
    """Specialized integration for Suffolk County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Suffolk County"
        super().__init__(jurisdiction_id, config)
