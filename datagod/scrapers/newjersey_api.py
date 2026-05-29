"""
New Jersey County Records API Integration
Integrates with New Jersey county tax and clerk APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class NewJerseyCountyAPI(BaseAPIIntegration):
    """
    Integration with New Jersey County Tax Assessor and County Clerk APIs
    Supports Bergen, Middlesex, Essex, Hudson, Monmouth and other major counties
    """

    COUNTY_APIS = {
        "bergen": {
            "base_url": "https://www.co.bergen.nj.us/tax/api",
            "clerk_url": "https://www.co.bergen.nj.us/clerk/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "middlesex": {
            "base_url": "https://www.middlesexcountynj.gov/tax/api",
            "clerk_url": "https://www.middlesexcountynj.gov/clerk/api",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "essex": {
            "base_url": "https://www.essexcountynj.org/tax/api",
            "clerk_url": "https://www.essexcountynj.org/clerk/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "hudson": {
            "base_url": "https://www.hudsoncountynj.org/tax/api",
            "clerk_url": "https://www.hudsoncountynj.org/clerk/api",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "monmouth": {
            "base_url": "https://www.visitmonmouth.com/tax/api",
            "clerk_url": "https://www.visitmonmouth.com/clerk/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "ocean": {
            "base_url": "https://www.co.ocean.nj.us/tax/api",
            "clerk_url": "https://www.co.ocean.nj.us/clerk/api",
            "features": ["property_search", "deed_records"],
        },
        "union": {
            "base_url": "https://www.ucnj.org/tax/api",
            "features": ["property_search", "tax_info"],
        },
        "passaic": {
            "base_url": "https://www.passaiccountynj.org/tax/api",
            "clerk_url": "https://www.passaiccountynj.org/clerk/api",
            "features": ["property_search", "deed_records"],
        },
        "camden": {
            "base_url": "https://www.camdencounty.com/tax/api",
            "features": ["property_search", "deed_records"],
        },
        "morris": {
            "base_url": "https://www.morriscountynj.gov/tax/api",
            "clerk_url": "https://www.morriscountynj.gov/clerk/api",
            "features": ["property_search", "deed_records", "tax_info"],
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
            logger.warning(f"No specific API config for NJ county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countynj.gov/tax/api"
            )
            self.clerk_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized New Jersey API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """NJ APIs typically use API key authentication"""
        if self.api_key:
            logger.info("API key authentication configured")
            return True
        logger.info("No authentication required for public API")
        return True

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for property and deed records"""
        results = []

        if "property_search" in self.available_features:
            results.extend(self._search_property_records(query))

        if "deed_records" in self.available_features:
            results.extend(self._search_deed_records(query))

        return results

    def _search_property_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search property tax records"""
        try:
            params = {
                "block_lot": query.get("property_id", ""),
                "owner": query.get("owner_name", ""),
                "address": query.get("address", ""),
                "municipality": query.get("city", ""),
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
        """Search deed/mortgage records from county clerk"""
        if not self.clerk_url:
            return []

        try:
            params = {
                "grantor": query.get("grantor", ""),
                "grantee": query.get("grantee", ""),
                "doc_type": query.get("record_type", "DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
            }
            params = {k: v for k, v in params.items() if v}

            original_url = self.base_url
            self.base_url = self.clerk_url

            response = self.make_request("GET", "documents/search", params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            records = data.get("documents", data.get("records", []))
            return [self._map_deed_to_standard(record) for record in records]

        except Exception as e:
            logger.error(f"Deed search failed for {self.county_name}: {e}")
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

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map NJ property data to standard format"""
        # NJ uses Block/Lot system for property identification
        block = data.get("block", "")
        lot = data.get("lot", "")
        qualifier = data.get("qualifier", "")
        block_lot = f"{block}/{lot}" + (f"/{qualifier}" if qualifier else "")

        return {
            "record_type": "property",
            "record_id": block_lot or data.get("property_id"),
            "title": f"Property - {data.get('property_location', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(
                data.get("total_assessment", 0) or data.get("net_value", 0)
            ),
            "address": data.get("property_location", ""),
            "city": data.get("municipality", ""),
            "state": "NJ",
            "zip_code": data.get("zip_code", ""),
            "date": data.get("last_sale_date"),
            "description": data.get("property_class_desc", ""),
            "raw_data": data,
            "data_source": f"nj_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map NJ deed record to standard format"""
        return {
            "record_type": data.get("document_type", "deed").lower(),
            "record_id": data.get("document_number") or data.get("instrument_number"),
            "title": f"{data.get('document_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(data.get("consideration", 0)),
            "address": data.get("property_address", ""),
            "city": data.get("municipality", ""),
            "state": "NJ",
            "date": data.get("recording_date") or data.get("dated"),
            "document_number": data.get("document_number"),
            "book_page": f"{data.get('book', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"nj_{self.county_name}_clerk",
            "scraped_at": datetime.now().isoformat(),
        }


class BergenCountyAPI(NewJerseyCountyAPI):
    """Specialized integration for Bergen County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Bergen County"
        super().__init__(jurisdiction_id, config)

    def get_sr1a_records(self, block: str, lot: str) -> List[Dict[str, Any]]:
        """Get SR1A (deed transfer) records (Bergen specific)"""
        try:
            response = self.make_request(
                "GET", "sr1a/search", params={"block": block, "lot": lot}
            )
            data = self.validate_response(response)
            return data.get("transfers", [])
        except Exception as e:
            logger.error(f"Failed to get SR1A records: {e}")
            return []


class MiddlesexCountyAPI(NewJerseyCountyAPI):
    """Specialized integration for Middlesex County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Middlesex County"
        super().__init__(jurisdiction_id, config)


class EssexCountyAPI(NewJerseyCountyAPI):
    """Specialized integration for Essex County (Newark)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Essex County"
        super().__init__(jurisdiction_id, config)


class HudsonCountyAPI(NewJerseyCountyAPI):
    """Specialized integration for Hudson County (Jersey City)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Hudson County"
        super().__init__(jurisdiction_id, config)


class MonmouthCountyAPI(NewJerseyCountyAPI):
    """Specialized integration for Monmouth County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Monmouth County"
        super().__init__(jurisdiction_id, config)
