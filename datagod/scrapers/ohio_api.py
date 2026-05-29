"""
Ohio County Records API Integration
Integrates with Ohio county auditor and recorder APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class OhioCountyAPI(BaseAPIIntegration):
    """
    Integration with Ohio County Auditor and Recorder APIs
    Supports Cuyahoga (Cleveland), Franklin (Columbus), Hamilton (Cincinnati),
    and other major counties
    """

    COUNTY_APIS = {
        "cuyahoga": {
            "base_url": "https://fiscalofficer.cuyahogacounty.us/api",
            "recorder_url": "https://recorder.cuyahogacounty.us/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "franklin": {
            "base_url": "https://property.franklincountyauditor.com/api",
            "recorder_url": "https://recorder.franklincountyohio.gov/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "hamilton": {
            "base_url": "https://wedge.hcauditor.org/api",
            "recorder_url": "https://recorder.hamilton-co.org/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "summit": {  # Akron
            "base_url": "https://www.co.summit.oh.us/api/auditor",
            "recorder_url": "https://www.co.summit.oh.us/api/recorder",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "montgomery": {  # Dayton
            "base_url": "https://www.mcauditor.org/api",
            "recorder_url": "https://www.mcrecorder.org/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "lucas": {  # Toledo
            "base_url": "https://www.co.lucas.oh.us/api/auditor",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "butler": {
            "base_url": "https://www.butlercountyauditor.org/api",
            "features": ["property_search", "deed_records"],
        },
        "stark": {  # Canton
            "base_url": "https://www.starkauditor.org/api",
            "features": ["property_search", "deed_records"],
        },
        "lorain": {
            "base_url": "https://www.loraincountyauditor.com/api",
            "features": ["property_search", "deed_records"],
        },
        "mahoning": {  # Youngstown
            "base_url": "https://www.mahoningcountyoh.gov/api/auditor",
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
            self.recorder_url = self.county_config.get("recorder_url", "")
            self.available_features = self.county_config.get("features", [])
        else:
            logger.warning(f"No specific API config for OH county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countyauditor.org/api"
            )
            self.recorder_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized Ohio API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with Ohio API"""
        if self.api_key:
            logger.info("OH API key authentication configured")
            return True
        logger.info("Using public access for OH records")
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
        """Search property assessment records from county auditor"""
        try:
            params = {
                "parcel": query.get("parcel_id", ""),
                "address": query.get("address", ""),
                "owner": query.get("owner_name", ""),
                "city": query.get("city", ""),
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
        """Search deed records from county recorder"""
        if not self.recorder_url:
            return []

        try:
            params = {
                "grantor": query.get("grantor", ""),
                "grantee": query.get("grantee", ""),
                "doc_type": query.get("doc_type", "WARRANTY DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            original_url = self.base_url
            self.base_url = self.recorder_url

            response = self.make_request("GET", "documents/search", params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            records = data.get("documents", data.get("records", []))
            return [self._map_deed_to_standard(record) for record in records]

        except Exception as e:
            logger.error(f"Deed search failed for {self.county_name}: {e}")
            return []

    def _search_mortgage_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search mortgage records"""
        if not self.recorder_url or "mortgage_records" not in self.available_features:
            return []

        try:
            params = {
                "mortgagor": query.get("borrower", query.get("mortgagor", "")),
                "mortgagee": query.get("lender", query.get("mortgagee", "")),
                "doc_type": "MORTGAGE",
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            original_url = self.base_url
            self.base_url = self.recorder_url

            response = self.make_request("GET", "documents/search", params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            mortgages = data.get("documents", [])
            return [self._map_mortgage_to_standard(m) for m in mortgages]

        except Exception as e:
            logger.error(f"Mortgage search failed for {self.county_name}: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed record information"""
        try:
            response = self.make_request("GET", f"properties/{record_id}")
            data = self.validate_response(response)
            return self._map_property_to_standard(data)
        except Exception as e:
            logger.error(f"Failed to get details for {record_id}: {e}")
            return {}

    def get_tax_info(self, parcel_id: str) -> Dict[str, Any]:
        """Get tax information for a property"""
        if "tax_info" not in self.available_features:
            return {}

        try:
            response = self.make_request("GET", f"properties/{parcel_id}/taxes")
            data = self.validate_response(response)
            return {
                "tax_year": data.get("tax_year"),
                "annual_tax": float(data.get("annual_tax", 0)),
                "tax_rate": float(data.get("tax_rate", 0)),
                "levies": data.get("levies", []),
                "special_assessments": data.get("special_assessments", []),
                "payment_status": data.get("payment_status"),
                "delinquent_amount": float(data.get("delinquent_amount", 0)),
            }
        except Exception as e:
            logger.error(f"Failed to get tax info: {e}")
            return {}

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Ohio property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("parcel_number") or data.get("parcel_id"),
            "title": f"Property - {data.get('situs_address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("market_value", 0)),
            "address": data.get("situs_address", ""),
            "city": data.get("city", ""),
            "state": "OH",
            "zip_code": data.get("zip_code", ""),
            "parcel_id": data.get("parcel_number", ""),
            "date": data.get("valuation_date"),
            "description": data.get("property_class", ""),
            "land_value": float(data.get("land_value", 0)),
            "improvement_value": float(data.get("improvement_value", 0)),
            "cauv_value": float(
                data.get("cauv_value", 0)
            ),  # Current Agricultural Use Value
            "raw_data": data,
            "data_source": f"ohio_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Ohio deed record to standard format"""
        return {
            "record_type": data.get("doc_type", "deed").lower().replace(" ", "_"),
            "record_id": data.get("instrument_number") or data.get("document_number"),
            "title": f"{data.get('doc_type', 'Warranty Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(data.get("consideration", 0)),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "OH",
            "parcel_id": data.get("parcel_number", ""),
            "date": data.get("recording_date"),
            "document_number": data.get("instrument_number"),
            "volume_page": f"{data.get('volume', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"ohio_{self.county_name}_recorder",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map mortgage record to standard format"""
        return {
            "record_type": "mortgage",
            "record_id": data.get("instrument_number"),
            "title": f"Mortgage - {data.get('mortgagor', 'Unknown')}",
            "grantor": data.get("mortgagor", ""),
            "grantee": data.get("mortgagee", ""),
            "borrower": data.get("mortgagor", ""),
            "lender": data.get("mortgagee", ""),
            "amount": float(data.get("loan_amount", 0)),
            "date": data.get("recording_date"),
            "document_number": data.get("instrument_number"),
            "volume_page": f"{data.get('volume', '')}/{data.get('page', '')}",
            "parcel_id": data.get("parcel_number", ""),
            "raw_data": data,
            "data_source": f"ohio_{self.county_name}_mortgage",
            "scraped_at": datetime.now().isoformat(),
        }


class CuyahogaCountyAPI(OhioCountyAPI):
    """Specialized integration for Cuyahoga County (Cleveland)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Cuyahoga County"
        super().__init__(jurisdiction_id, config)


class FranklinCountyAPI(OhioCountyAPI):
    """Specialized integration for Franklin County (Columbus)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Franklin County"
        super().__init__(jurisdiction_id, config)


class HamiltonCountyAPI(OhioCountyAPI):
    """Specialized integration for Hamilton County (Cincinnati)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Hamilton County"
        super().__init__(jurisdiction_id, config)
