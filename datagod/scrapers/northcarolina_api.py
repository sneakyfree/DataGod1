"""
North Carolina County Records API Integration
Integrates with North Carolina county tax and register of deeds APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class NorthCarolinaCountyAPI(BaseAPIIntegration):
    """
    Integration with North Carolina County Tax and Register of Deeds APIs
    Supports Mecklenburg, Wake, Guilford, Forsyth, Durham and other major counties
    """

    COUNTY_APIS = {
        "mecklenburg": {
            "base_url": "https://property.spatialest.com/nc/mecklenburg/api",
            "rod_url": "https://www.mecknc.gov/rod/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "wake": {
            "base_url": "https://services.wakegov.com/realestate/api",
            "rod_url": "https://www.wakegov.com/rod/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "guilford": {
            "base_url": "https://www.guilfordcountync.gov/tax/api",
            "rod_url": "https://www.guilfordcountync.gov/rod/api",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "forsyth": {
            "base_url": "https://www.forsyth.cc/tax/api",
            "rod_url": "https://www.forsyth.cc/rod/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "durham": {
            "base_url": "https://www.dconc.gov/tax/api",
            "rod_url": "https://www.dconc.gov/rod/api",
            "features": ["property_search", "deed_records"],
        },
        "cumberland": {
            "base_url": "https://www.co.cumberland.nc.us/tax/api",
            "features": ["property_search", "tax_info"],
        },
        "buncombe": {
            "base_url": "https://www.buncombecounty.org/tax/api",
            "rod_url": "https://www.buncombecounty.org/rod/api",
            "features": ["property_search", "deed_records"],
        },
        "union": {
            "base_url": "https://www.unioncountync.gov/tax/api",
            "features": ["property_search", "deed_records"],
        },
        "cabarrus": {
            "base_url": "https://www.cabarruscounty.us/tax/api",
            "features": ["property_search", "tax_info"],
        },
        "new-hanover": {
            "base_url": "https://www.nhcgov.com/tax/api",
            "rod_url": "https://www.nhcgov.com/rod/api",
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
            self.rod_url = self.county_config.get("rod_url", "")
            self.available_features = self.county_config.get("features", [])
        else:
            logger.warning(f"No specific API config for NC county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}countync.gov/tax/api"
            )
            self.rod_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized North Carolina API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """NC APIs typically use API key authentication"""
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
                "pin": query.get("property_id", ""),
                "owner": query.get("owner_name", ""),
                "address": query.get("address", ""),
                "city": query.get("city", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "parcels/search", params=params)
            data = self.validate_response(response)

            properties = data.get("parcels", data.get("results", []))
            return [self._map_property_to_standard(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Property search failed for {self.county_name}: {e}")
            return []

    def _search_deed_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search deed/mortgage records from register of deeds"""
        if not self.rod_url:
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
            self.base_url = self.rod_url

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
            response = self.make_request("GET", f"parcels/{record_id}")
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
        """Map NC property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("pin") or data.get("parcel_id"),
            "title": f"Property - {data.get('property_address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("total_value", 0) or data.get("tax_value", 0)),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "NC",
            "zip_code": data.get("zip_code", ""),
            "date": data.get("last_sale_date"),
            "description": data.get("legal_description", ""),
            "raw_data": data,
            "data_source": f"nc_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map NC deed record to standard format"""
        return {
            "record_type": data.get("document_type", "deed").lower(),
            "record_id": data.get("instrument_number") or data.get("document_number"),
            "title": f"{data.get('document_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(
                data.get("consideration", 0) or data.get("excise_tax", 0) * 500
            ),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "NC",
            "date": data.get("recording_date") or data.get("filed_date"),
            "document_number": data.get("instrument_number"),
            "book_page": f"{data.get('book', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"nc_{self.county_name}_rod",
            "scraped_at": datetime.now().isoformat(),
        }


class MecklenburgCountyAPI(NorthCarolinaCountyAPI):
    """Specialized integration for Mecklenburg County (Charlotte)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Mecklenburg County"
        super().__init__(jurisdiction_id, config)

    def get_sales_history(self, pin: str) -> List[Dict[str, Any]]:
        """Get sales history for a parcel (Mecklenburg specific)"""
        try:
            response = self.make_request("GET", f"parcels/{pin}/sales")
            data = self.validate_response(response)
            return data.get("sales", [])
        except Exception as e:
            logger.error(f"Failed to get sales history: {e}")
            return []


class WakeCountyAPI(NorthCarolinaCountyAPI):
    """Specialized integration for Wake County (Raleigh)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Wake County"
        super().__init__(jurisdiction_id, config)

    def get_imaps_data(self, pin: str) -> Dict[str, Any]:
        """Get iMAPS GIS data for a parcel (Wake specific)"""
        try:
            response = self.make_request("GET", f"parcels/{pin}/gis")
            data = self.validate_response(response)
            return {
                "acres": data.get("calculated_acres"),
                "land_class": data.get("land_class_code"),
                "zoning": data.get("zoning"),
                "school_district": data.get("school_district"),
            }
        except Exception as e:
            logger.error(f"Failed to get iMAPS data: {e}")
            return {}


class GuilfordCountyAPI(NorthCarolinaCountyAPI):
    """Specialized integration for Guilford County (Greensboro)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Guilford County"
        super().__init__(jurisdiction_id, config)


class DurhamCountyAPI(NorthCarolinaCountyAPI):
    """Specialized integration for Durham County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Durham County"
        super().__init__(jurisdiction_id, config)
