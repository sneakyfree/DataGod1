"""
Arizona County Records API Integration
Integrates with Arizona county assessor and recorder APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class ArizonaCountyAPI(BaseAPIIntegration):
    """
    Integration with Arizona County Assessor and Recorder APIs
    Supports Maricopa (Phoenix), Pima (Tucson), and other major counties
    """

    COUNTY_APIS = {
        "maricopa": {
            "base_url": "https://recorder.maricopa.gov/api",
            "assessor_url": "https://mcassessor.maricopa.gov/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
                "liens",
            ],
        },
        "pima": {
            "base_url": "https://www.recorder.pima.gov/api",
            "assessor_url": "https://www.asr.pima.gov/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "pinal": {
            "base_url": "https://www.pinalcountyaz.gov/api/recorder",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "yavapai": {
            "base_url": "https://www.yavapai.us/api/recorder",
            "features": ["property_search", "deed_records"],
        },
        "mohave": {
            "base_url": "https://www.mohavecounty.us/api/recorder",
            "features": ["property_search", "deed_records"],
        },
        "yuma": {
            "base_url": "https://www.yumacountyaz.gov/api/recorder",
            "features": ["property_search", "deed_records"],
        },
        "cochise": {
            "base_url": "https://www.cochise.az.gov/api/recorder",
            "features": ["property_search", "deed_records"],
        },
        "coconino": {
            "base_url": "https://www.coconino.az.gov/api/recorder",
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
            logger.warning(f"No specific API config for AZ county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countyaz.gov/api/recorder"
            )
            self.assessor_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized Arizona API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with Arizona API"""
        if self.api_key:
            logger.info("AZ API key authentication configured")
            return True
        logger.info("Using public access for AZ records")
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
                "parcel": query.get("parcel_id", ""),
                "address": query.get("address", ""),
                "owner": query.get("owner_name", ""),
                "city": query.get("city", ""),
            }
            params = {k: v for k, v in params.items() if v}

            # Use assessor URL if available
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
        """Search deed records from county recorder"""
        try:
            params = {
                "grantor": query.get("grantor", ""),
                "grantee": query.get("grantee", ""),
                "doc_type": query.get("doc_type", "WARRANTY DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
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
        """Search mortgage/deed of trust records"""
        if "mortgage_records" not in self.available_features:
            return []

        try:
            params = {
                "trustor": query.get("borrower", query.get("trustor", "")),
                "beneficiary": query.get("lender", query.get("beneficiary", "")),
                "doc_type": "DEED OF TRUST",
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "documents/search", params=params)
            data = self.validate_response(response)

            mortgages = data.get("documents", [])
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

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Arizona property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("parcel_number") or data.get("apn"),
            "title": f"Property - {data.get('situs_address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("full_cash_value", 0)),
            "address": data.get("situs_address", ""),
            "city": data.get("city", ""),
            "state": "AZ",
            "zip_code": data.get("zip_code", ""),
            "parcel_id": data.get("parcel_number", ""),
            "date": data.get("valuation_date"),
            "description": data.get("property_class", ""),
            "land_value": float(data.get("land_value", 0)),
            "improvement_value": float(data.get("improvement_value", 0)),
            "raw_data": data,
            "data_source": f"arizona_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Arizona deed record to standard format"""
        return {
            "record_type": data.get("doc_type", "deed").lower().replace(" ", "_"),
            "record_id": data.get("recording_number") or data.get("document_number"),
            "title": f"{data.get('doc_type', 'Warranty Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(data.get("consideration", 0)),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "AZ",
            "parcel_id": data.get("parcel_number", ""),
            "date": data.get("recording_date"),
            "document_number": data.get("recording_number"),
            "docket_page": f"{data.get('docket', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"arizona_{self.county_name}_recorder",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map deed of trust to standard mortgage format"""
        return {
            "record_type": "mortgage",
            "record_id": data.get("recording_number"),
            "title": f"Deed of Trust - {data.get('trustor', 'Unknown')}",
            "grantor": data.get("trustor", ""),
            "grantee": data.get("beneficiary", ""),
            "borrower": data.get("trustor", ""),
            "lender": data.get("beneficiary", ""),
            "trustee": data.get("trustee", ""),
            "amount": float(data.get("loan_amount", 0)),
            "date": data.get("recording_date"),
            "document_number": data.get("recording_number"),
            "parcel_id": data.get("parcel_number", ""),
            "raw_data": data,
            "data_source": f"arizona_{self.county_name}_mortgage",
            "scraped_at": datetime.now().isoformat(),
        }


class MaricopaCountyAPI(ArizonaCountyAPI):
    """Specialized integration for Maricopa County (Phoenix)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Maricopa County"
        super().__init__(jurisdiction_id, config)

    def get_lien_info(self, parcel_id: str) -> List[Dict[str, Any]]:
        """Get lien information (Maricopa specific)"""
        if "liens" not in self.available_features:
            return []

        try:
            response = self.make_request("GET", f"properties/{parcel_id}/liens")
            data = self.validate_response(response)

            liens = data.get("liens", [])
            return [
                {
                    "lien_type": lien.get("lien_type"),
                    "lien_amount": float(lien.get("amount", 0)),
                    "recording_date": lien.get("recording_date"),
                    "release_date": lien.get("release_date"),
                    "creditor": lien.get("creditor"),
                    "status": lien.get("status"),
                }
                for lien in liens
            ]

        except Exception as e:
            logger.error(f"Failed to get lien info: {e}")
            return []


class PimaCountyAPI(ArizonaCountyAPI):
    """Specialized integration for Pima County (Tucson)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Pima County"
        super().__init__(jurisdiction_id, config)
