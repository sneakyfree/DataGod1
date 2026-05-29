"""
Florida Property Appraiser API Integration
Integrates with Florida county property appraiser APIs for property records
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import (
    APIKeyAuthentication,
    BaseAPIIntegration,
)

logger = logging.getLogger(__name__)


class FloridaPropertyAppraiserAPI(BaseAPIIntegration, APIKeyAuthentication):
    """
    Integration with Florida Property Appraiser APIs
    Supports multiple Florida counties with standardized interfaces
    """

    # County codes and their API endpoints
    COUNTY_APIS = {
        "miami-dade": {
            "base_url": "https://www.miamiappraiser.com/api",
            "features": ["property_search", "sales_history", "tax_info"],
        },
        "broward": {
            "base_url": "https://www.browardappraiser.com/api",
            "features": ["property_search", "permits", "sales_history"],
        },
        "palm-beach": {
            "base_url": "https://www.pbcgov.org/papa/api",
            "features": ["property_search", "value_history", "comparables"],
        },
        "hillsborough": {
            "base_url": "https://www.hcpafl.org/api",
            "features": ["property_search", "sales_history", "tax_roll"],
        },
        "orange": {
            "base_url": "https://www.orangecao.org/api",
            "features": ["property_search", "permits", "sales_history"],
        },
        "duval": {
            "base_url": "https://www.coj.net/api",
            "features": ["property_search", "tax_info", "sales_history"],
        },
    }

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        # Extract county from jurisdiction name
        self.county_name = self._extract_county_name(
            config.get("jurisdiction_name", "")
        )
        self.county_config = self.COUNTY_APIS.get(
            self.county_name.lower().replace(" ", "-")
        )

        if not self.county_config:
            logger.warning(f"No specific API config for county: {self.county_name}")
            # Use generic Florida API structure
            self.county_config = {
                "base_url": f"https://www.{self.county_name.lower().replace(' ', '')}appraiser.com/api",
                "features": ["property_search", "sales_history"],
            }

        # Update base URL
        self.base_url = self.county_config["base_url"]
        self.available_features = self.county_config["features"]

        logger.info(f"Initialized Florida API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        # Handle different naming conventions
        name = jurisdiction_name.lower()

        # Remove "county" suffix if present
        if name.endswith(" county"):
            name = name[:-7]

        # Handle special cases
        if "miami-dade" in name:
            return "miami-dade"
        elif "palm beach" in name:
            return "palm-beach"
        elif "st. johns" in name:
            return "st-johns"

        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with Florida Property Appraiser API"""
        # Most Florida county APIs use simple API key authentication
        return super().authenticate()

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        Search for property records using Florida API

        Supported query parameters:
        - folio_number: Property folio/ID number
        - address: Street address
        - owner_name: Property owner name
        - zip_code: ZIP code
        - property_use: Residential, Commercial, etc.
        """
        if "property_search" not in self.available_features:
            logger.warning(f"Property search not available for {self.county_name}")
            return []

        try:
            # Build search parameters
            search_params = self._build_search_params(query)

            response = self.make_request(
                "GET", "properties/search", params=search_params
            )
            data = self.validate_response(response)

            # Extract properties from response
            properties = data.get("properties", [])
            logger.info(f"Found {len(properties)} properties in {self.county_name}")

            # Convert to standard format
            return [self.map_api_data_to_standard_format(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Search failed for {self.county_name}: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed property information"""
        try:
            response = self.make_request("GET", f"properties/{record_id}")
            data = self.validate_response(response)

            return self.map_api_data_to_standard_format(data)

        except Exception as e:
            logger.error(f"Failed to get details for record {record_id}: {e}")
            return {}

    def get_sales_history(self, record_id: str) -> List[Dict[str, Any]]:
        """Get sales history for a property"""
        if "sales_history" not in self.available_features:
            return []

        try:
            response = self.make_request("GET", f"properties/{record_id}/sales")
            data = self.validate_response(response)

            sales = data.get("sales_history", [])
            return [self._map_sale_to_standard_format(sale) for sale in sales]

        except Exception as e:
            logger.error(f"Failed to get sales history for {record_id}: {e}")
            return []

    def get_tax_information(self, record_id: str) -> Dict[str, Any]:
        """Get tax information for a property"""
        if "tax_info" not in self.available_features:
            return {}

        try:
            response = self.make_request("GET", f"properties/{record_id}/taxes")
            data = self.validate_response(response)

            return {
                "tax_year": data.get("tax_year"),
                "assessed_value": data.get("assessed_value"),
                "tax_rate": data.get("tax_rate"),
                "annual_tax": data.get("annual_tax"),
                "last_payment_date": data.get("last_payment_date"),
                "delinquent": data.get("delinquent", False),
            }

        except Exception as e:
            logger.error(f"Failed to get tax info for {record_id}: {e}")
            return {}

    def _build_search_params(self, query: Dict[str, Any]) -> Dict[str, str]:
        """Build search parameters for API request"""
        params = {}

        # Map query fields to API parameters
        field_mapping = {
            "folio_number": "folio",
            "address": "address",
            "owner_name": "owner",
            "zip_code": "zip",
            "property_use": "use_code",
        }

        for query_field, api_field in field_mapping.items():
            if query_field in query and query[query_field]:
                params[api_field] = str(query[query_field])

        # Add date range if specified
        if "date_from" in query:
            params["sale_date_from"] = query["date_from"]
        if "date_to" in query:
            params["sale_date_to"] = query["date_to"]

        return params

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map Florida API data to DataGod standard format"""
        return {
            "property_id": api_data.get("folio_number") or api_data.get("property_id"),
            "borrower_name": api_data.get("owner_name", ""),
            "lender_name": "",  # Not typically in property records
            "loan_amount": 0.0,  # Property records don't have loan amounts
            "loan_type": "Unknown",
            "interest_rate": 0.0,
            "loan_term": 0,
            "loan_date": api_data.get("last_sale_date", ""),
            "property_address": self._format_address(api_data),
            "property_value": float(api_data.get("assessed_value", 0)),
            "status": "active",
            "data_source": f"florida_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
            "additional_data": {
                "building_sqft": api_data.get("building_area"),
                "land_sqft": api_data.get("land_area"),
                "year_built": api_data.get("year_built"),
                "property_use": api_data.get("property_use"),
                "neighborhood": api_data.get("neighborhood"),
                "subdivision": api_data.get("subdivision"),
                "legal_description": api_data.get("legal_description"),
            },
        }

    def _map_sale_to_standard_format(self, sale_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map sale data to standard format"""
        return {
            "sale_date": sale_data.get("sale_date"),
            "sale_price": float(sale_data.get("sale_price", 0)),
            "sale_type": sale_data.get("sale_type", "Unknown"),
            "buyer_name": sale_data.get("buyer_name", ""),
            "seller_name": sale_data.get("seller_name", ""),
            "document_number": sale_data.get("document_number"),
            "book_page": sale_data.get("book_page"),
        }

    def _format_address(self, api_data: Dict[str, Any]) -> str:
        """Format address from API data"""
        address_parts = []

        if api_data.get("site_address"):
            address_parts.append(api_data["site_address"])

        city_state_zip = []
        if api_data.get("city"):
            city_state_zip.append(api_data["city"])
        if api_data.get("state", "FL"):
            city_state_zip.append(api_data["state"])
        if api_data.get("zip_code"):
            city_state_zip.append(api_data["zip_code"])

        if city_state_zip:
            address_parts.append(", ".join(city_state_zip))

        return " ".join(address_parts)


class FloridaMiamiDadeAPI(FloridaPropertyAppraiserAPI):
    """Specialized integration for Miami-Dade County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Miami-Dade County"
        super().__init__(jurisdiction_id, config)

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Miami-Dade specific search with additional features"""
        # Miami-Dade has a more sophisticated API
        results = super().search_records(query, **kwargs)

        # Add Miami-Dade specific enrichment if needed
        for result in results:
            if result.get("additional_data"):
                # Add zoning information if available
                result["additional_data"][
                    "zoning_code"
                ] = "TBD"  # Would call separate zoning API

        return results


class FloridaBrowardAPI(FloridaPropertyAppraiserAPI):
    """Specialized integration for Broward County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Broward County"
        super().__init__(jurisdiction_id, config)

    def get_permit_history(self, record_id: str) -> List[Dict[str, Any]]:
        """Get building permit history (Broward specific)"""
        if "permits" not in self.available_features:
            return []

        try:
            response = self.make_request("GET", f"properties/{record_id}/permits")
            data = self.validate_response(response)

            permits = data.get("permits", [])
            return [self._map_permit_to_standard_format(permit) for permit in permits]

        except Exception as e:
            logger.error(f"Failed to get permits for {record_id}: {e}")
            return []

    def _map_permit_to_standard_format(
        self, permit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map permit data to standard format"""
        return {
            "permit_number": permit_data.get("permit_number"),
            "permit_type": permit_data.get("permit_type"),
            "issue_date": permit_data.get("issue_date"),
            "final_date": permit_data.get("final_date"),
            "status": permit_data.get("status"),
            "description": permit_data.get("description"),
            "value": float(permit_data.get("value", 0)),
        }
