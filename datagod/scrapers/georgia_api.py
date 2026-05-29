"""
Georgia County Records API Integration
Integrates with Georgia county superior court clerk and tax assessor APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class GeorgiaCountyAPI(BaseAPIIntegration):
    """
    Integration with Georgia County Superior Court Clerk and Tax Assessor APIs
    Supports Fulton (Atlanta), DeKalb, Cobb, Gwinnett, and other major counties
    """

    COUNTY_APIS = {
        "fulton": {
            "base_url": "https://www.fultoncountyga.gov/api/clerk",
            "assessor_url": "https://www.fultoncountyga.gov/api/assessor",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
                "ucc_filings",
            ],
        },
        "dekalb": {
            "base_url": "https://www.dekalbcountyga.gov/api/clerk",
            "assessor_url": "https://www.dekalbcountyga.gov/api/assessor",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "cobb": {
            "base_url": "https://www.cobbcounty.org/api/clerk",
            "assessor_url": "https://www.cobbcounty.org/api/assessor",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "gwinnett": {
            "base_url": "https://www.gwinnettcounty.com/api/clerk",
            "assessor_url": "https://www.gwinnettcounty.com/api/assessor",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "chatham": {  # Savannah
            "base_url": "https://www.chathamcounty.org/api/clerk",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "clayton": {
            "base_url": "https://www.claytoncountyga.gov/api/clerk",
            "features": ["property_search", "deed_records"],
        },
        "cherokee": {
            "base_url": "https://www.cherokeega.com/api/clerk",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "forsyth": {
            "base_url": "https://www.forsythco.com/api/clerk",
            "features": ["property_search", "deed_records"],
        },
        "henry": {
            "base_url": "https://www.co.henry.ga.us/api/clerk",
            "features": ["property_search", "deed_records"],
        },
        "hall": {
            "base_url": "https://www.hallcounty.org/api/clerk",
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
            self.assessor_url = self.county_config.get("assessor_url", "")
            self.available_features = self.county_config.get("features", [])
        else:
            logger.warning(f"No specific API config for GA county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countyga.gov/api/clerk"
            )
            self.assessor_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized Georgia API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with Georgia API"""
        if self.api_key:
            logger.info("GA API key authentication configured")
            return True
        logger.info("Using public access for GA records")
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
                "parcel_id": query.get("parcel_id", ""),
                "address": query.get("address", ""),
                "owner": query.get("owner_name", ""),
                "city": query.get("city", ""),
            }
            params = {k: v for k, v in params.items() if v}

            if self.assessor_url:
                original_url = self.base_url
                self.base_url = self.assessor_url

            response = self.make_request("GET", "properties/search", params=params)
            data = self.validate_response(response)

            if self.assessor_url:
                self.base_url = original_url

            properties = data.get("properties", data.get("results", []))
            return [self._map_property_to_standard(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Property search failed for {self.county_name}: {e}")
            return []

    def _search_deed_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search deed records from county superior court clerk"""
        try:
            params = {
                "grantor": query.get("grantor", ""),
                "grantee": query.get("grantee", ""),
                "doc_type": query.get("doc_type", "WARRANTY DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "deeds/search", params=params)
            data = self.validate_response(response)

            records = data.get("deeds", data.get("documents", []))
            return [self._map_deed_to_standard(record) for record in records]

        except Exception as e:
            logger.error(f"Deed search failed for {self.county_name}: {e}")
            return []

    def _search_mortgage_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search security deed records (Georgia uses Security Deeds instead of mortgages)"""
        if "mortgage_records" not in self.available_features:
            return []

        try:
            params = {
                "grantor": query.get("borrower", query.get("grantor", "")),
                "grantee": query.get("lender", query.get("grantee", "")),
                "doc_type": "SECURITY DEED",
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "deeds/search", params=params)
            data = self.validate_response(response)

            mortgages = data.get("deeds", [])
            return [self._map_mortgage_to_standard(m) for m in mortgages]

        except Exception as e:
            logger.error(f"Security deed search failed for {self.county_name}: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed record information"""
        try:
            response = self.make_request("GET", f"deeds/{record_id}")
            data = self.validate_response(response)
            return self._map_deed_to_standard(data)
        except Exception as e:
            logger.error(f"Failed to get details for {record_id}: {e}")
            return {}

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Georgia property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("parcel_id") or data.get("pin"),
            "title": f"Property - {data.get('situs_address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("fair_market_value", 0)),
            "address": data.get("situs_address", ""),
            "city": data.get("city", ""),
            "state": "GA",
            "zip_code": data.get("zip_code", ""),
            "parcel_id": data.get("parcel_id", ""),
            "date": data.get("digest_year"),
            "description": data.get("property_class", ""),
            "land_value": float(data.get("land_value", 0)),
            "improvement_value": float(data.get("improvement_value", 0)),
            "raw_data": data,
            "data_source": f"georgia_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Georgia deed record to standard format"""
        return {
            "record_type": data.get("doc_type", "deed").lower().replace(" ", "_"),
            "record_id": data.get("deed_book_page") or data.get("instrument_number"),
            "title": f"{data.get('doc_type', 'Warranty Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(data.get("consideration", 0)),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "GA",
            "parcel_id": data.get("parcel_id", ""),
            "date": data.get("recording_date"),
            "document_number": data.get("instrument_number"),
            "book_page": f"{data.get('deed_book', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"georgia_{self.county_name}_clerk",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map security deed to standard mortgage format"""
        return {
            "record_type": "mortgage",
            "record_id": data.get("deed_book_page") or data.get("instrument_number"),
            "title": f"Security Deed - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),  # Borrower in GA
            "grantee": data.get("grantee", ""),  # Lender in GA
            "borrower": data.get("grantor", ""),
            "lender": data.get("grantee", ""),
            "amount": float(data.get("loan_amount", data.get("consideration", 0))),
            "date": data.get("recording_date"),
            "document_number": data.get("instrument_number"),
            "book_page": f"{data.get('deed_book', '')}/{data.get('page', '')}",
            "parcel_id": data.get("parcel_id", ""),
            "raw_data": data,
            "data_source": f"georgia_{self.county_name}_mortgage",
            "scraped_at": datetime.now().isoformat(),
        }


class FultonCountyAPI(GeorgiaCountyAPI):
    """Specialized integration for Fulton County (Atlanta)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Fulton County"
        super().__init__(jurisdiction_id, config)

    def get_ucc_filings(self, debtor_name: str) -> List[Dict[str, Any]]:
        """Get UCC filings (Fulton specific)"""
        if "ucc_filings" not in self.available_features:
            return []

        try:
            response = self.make_request(
                "GET", "ucc/search", params={"debtor": debtor_name}
            )
            data = self.validate_response(response)

            filings = data.get("filings", [])
            return [
                {
                    "filing_number": f.get("filing_number"),
                    "filing_date": f.get("filing_date"),
                    "debtor_name": f.get("debtor_name"),
                    "secured_party": f.get("secured_party"),
                    "collateral": f.get("collateral_description"),
                    "status": f.get("status"),
                }
                for f in filings
            ]

        except Exception as e:
            logger.error(f"Failed to get UCC filings: {e}")
            return []


class DeKalbCountyAPI(GeorgiaCountyAPI):
    """Specialized integration for DeKalb County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "DeKalb County"
        super().__init__(jurisdiction_id, config)


class CobbCountyAPI(GeorgiaCountyAPI):
    """Specialized integration for Cobb County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Cobb County"
        super().__init__(jurisdiction_id, config)


class GwinnettCountyAPI(GeorgiaCountyAPI):
    """Specialized integration for Gwinnett County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Gwinnett County"
        super().__init__(jurisdiction_id, config)
