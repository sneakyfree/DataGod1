"""
California County Records API Integration
Integrates with California county assessor, recorder, and Secretary of State APIs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import (
    APIKeyAuthentication,
    BaseAPIIntegration,
)

logger = logging.getLogger(__name__)


class CaliforniaCountyAPI(BaseAPIIntegration):
    """
    Integration with California County Assessor and Recorder APIs
    Supports major California counties
    """

    COUNTY_APIS = {
        "los-angeles": {
            "base_url": "https://portal.assessor.lacounty.gov/api",
            "recorder_url": "https://www.lavote.net/api/recorder",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
                "assessor_maps",
            ],
        },
        "san-diego": {
            "base_url": "https://arcc.sdcounty.ca.gov/api",
            "recorder_url": "https://arcc.sdcounty.ca.gov/api/recorder",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "orange": {
            "base_url": "https://ocgov.com/api/assessor",
            "recorder_url": "https://ocrecorder.com/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "riverside": {
            "base_url": "https://www.asrclkrec.com/api/assessor",
            "recorder_url": "https://www.asrclkrec.com/api/recorder",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "san-bernardino": {
            "base_url": "https://www.sbcounty.gov/api/assessor",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "santa-clara": {
            "base_url": "https://www.sccassessor.org/api",
            "recorder_url": "https://recorderonline.sccgov.org/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "alameda": {
            "base_url": "https://www.acgov.org/api/assessor",
            "recorder_url": "https://www.acgov.org/api/recorder",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "sacramento": {
            "base_url": "https://assessorparcelviewer.saccounty.net/api",
            "recorder_url": "https://recorderonline.saccounty.net/api",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "contra-costa": {
            "base_url": "https://www.contracosta.ca.gov/api/assessor",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "fresno": {
            "base_url": "https://www.co.fresno.ca.us/api/assessor",
            "features": ["property_search", "deed_records"],
        },
        "san-francisco": {
            "base_url": "https://sfassessor.org/api",
            "recorder_url": "https://sfgov.org/recorder/api",
            "features": [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
            ],
        },
        "kern": {
            "base_url": "https://www.kerncounty.com/api/assessor",
            "features": ["property_search", "deed_records"],
        },
        "ventura": {
            "base_url": "https://recorder.countyofventura.org/api",
            "features": ["property_search", "deed_records", "mortgage_records"],
        },
        "san-mateo": {
            "base_url": "https://www.smcacre.org/api",
            "features": ["property_search", "deed_records", "tax_info"],
        },
        "san-joaquin": {
            "base_url": "https://www.sjgov.org/api/assessor",
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
            logger.warning(f"No specific API config for CA county: {self.county_name}")
            self.base_url = (
                f"https://www.{self.county_name.lower()}county.ca.gov/api/assessor"
            )
            self.recorder_url = ""
            self.available_features = ["property_search"]

        logger.info(f"Initialized California API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(" county"):
            name = name[:-7]
        return name.replace(" ", "-")

    def authenticate(self) -> bool:
        """Authenticate with California API"""
        if self.api_key:
            logger.info("CA API key authentication configured")
            return True
        logger.info("Using public access for CA records")
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
                "apn": query.get("apn", ""),  # Assessor Parcel Number
                "address": query.get("address", ""),
                "owner": query.get("owner_name", ""),
                "city": query.get("city", ""),
                "zip": query.get("zip_code", ""),
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request("GET", "parcels/search", params=params)
            data = self.validate_response(response)

            properties = data.get(
                "parcels", data.get("properties", data.get("results", []))
            )
            return [self._map_property_to_standard(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Property search failed for {self.county_name}: {e}")
            return []

    def _search_deed_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search deed/grant deed records from county recorder"""
        if not self.recorder_url:
            return []

        try:
            params = {
                "grantor": query.get("grantor", ""),
                "grantee": query.get("grantee", ""),
                "doc_type": query.get("doc_type", "GRANT DEED"),
                "date_from": query.get("date_from", ""),
                "date_to": query.get("date_to", ""),
                "apn": query.get("apn", ""),
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
        """Search deed of trust/mortgage records"""
        if not self.recorder_url or "mortgage_records" not in self.available_features:
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
            response = self.make_request("GET", f"parcels/{record_id}")
            data = self.validate_response(response)
            return self._map_property_to_standard(data)
        except Exception as e:
            logger.error(f"Failed to get details for {record_id}: {e}")
            return {}

    def get_prop_13_info(self, apn: str) -> Dict[str, Any]:
        """Get Proposition 13 base year value information"""
        if "tax_info" not in self.available_features:
            return {}

        try:
            response = self.make_request("GET", f"parcels/{apn}/prop13")
            data = self.validate_response(response)
            return {
                "base_year": data.get("base_year"),
                "base_value": float(data.get("base_value", 0)),
                "current_value": float(data.get("current_value", 0)),
                "transfer_history": data.get("transfers", []),
            }
        except Exception as e:
            logger.error(f"Failed to get Prop 13 info: {e}")
            return {}

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map California property data to standard format"""
        return {
            "record_type": "property",
            "record_id": data.get("apn") or data.get("parcel_number"),
            "title": f"Property - {data.get('situs_address', 'Unknown Address')}",
            "grantor": "",
            "grantee": data.get("owner_name", ""),
            "amount": float(data.get("assessed_value", 0)),
            "address": data.get("situs_address", ""),
            "city": data.get("city", ""),
            "state": "CA",
            "zip_code": data.get("zip_code", ""),
            "apn": data.get("apn", ""),
            "date": data.get("assessment_date"),
            "description": data.get("use_code_description", ""),
            "land_value": float(data.get("land_value", 0)),
            "improvement_value": float(data.get("improvement_value", 0)),
            "raw_data": data,
            "data_source": f"california_{self.county_name}_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map California deed record to standard format"""
        return {
            "record_type": data.get("doc_type", "deed").lower().replace(" ", "_"),
            "record_id": data.get("document_number") or data.get("recording_number"),
            "title": f"{data.get('doc_type', 'Grant Deed')} - {data.get('grantor', 'Unknown')}",
            "grantor": data.get("grantor", ""),
            "grantee": data.get("grantee", ""),
            "amount": float(
                data.get("consideration", data.get("transfer_tax", 0)) * 1000 / 1.1
                if data.get("transfer_tax")
                else 0
            ),
            "address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": "CA",
            "apn": data.get("apn", ""),
            "date": data.get("recording_date"),
            "document_number": data.get("document_number"),
            "book_page": f"{data.get('book', '')}/{data.get('page', '')}",
            "raw_data": data,
            "data_source": f"california_{self.county_name}_recorder",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map deed of trust to standard mortgage format"""
        return {
            "record_type": "mortgage",
            "record_id": data.get("document_number"),
            "title": f"Deed of Trust - {data.get('trustor', 'Unknown')}",
            "grantor": data.get("trustor", ""),  # Borrower in CA
            "grantee": data.get("beneficiary", ""),  # Lender in CA
            "borrower": data.get("trustor", ""),
            "lender": data.get("beneficiary", ""),
            "trustee": data.get("trustee", ""),
            "amount": float(data.get("loan_amount", 0)),
            "date": data.get("recording_date"),
            "document_number": data.get("document_number"),
            "apn": data.get("apn", ""),
            "raw_data": data,
            "data_source": f"california_{self.county_name}_mortgage",
            "scraped_at": datetime.now().isoformat(),
        }


class LosAngelesCountyAPI(CaliforniaCountyAPI):
    """Specialized integration for Los Angeles County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Los Angeles County"
        super().__init__(jurisdiction_id, config)

    def get_assessor_map(self, apn: str) -> Dict[str, Any]:
        """Get assessor map information (LA specific)"""
        if "assessor_maps" not in self.available_features:
            return {}

        try:
            response = self.make_request("GET", f"parcels/{apn}/map")
            data = self.validate_response(response)
            return {
                "map_book": data.get("map_book"),
                "map_page": data.get("map_page"),
                "tract_number": data.get("tract_number"),
                "lot_number": data.get("lot_number"),
                "map_url": data.get("map_url"),
            }
        except Exception as e:
            logger.error(f"Failed to get assessor map: {e}")
            return {}


class SanDiegoCountyAPI(CaliforniaCountyAPI):
    """Specialized integration for San Diego County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "San Diego County"
        super().__init__(jurisdiction_id, config)


class SanFranciscoCountyAPI(CaliforniaCountyAPI):
    """Specialized integration for San Francisco County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "San Francisco County"
        super().__init__(jurisdiction_id, config)

    def get_rent_control_info(self, apn: str) -> Dict[str, Any]:
        """Get rent control status (SF specific)"""
        try:
            response = self.make_request("GET", f"parcels/{apn}/rent-control")
            data = self.validate_response(response)
            return {
                "rent_controlled": data.get("is_rent_controlled", False),
                "unit_count": data.get("unit_count"),
                "exemptions": data.get("exemptions", []),
            }
        except Exception as e:
            logger.error(f"Failed to get rent control info: {e}")
            return {}


class SantaClaraCountyAPI(CaliforniaCountyAPI):
    """Specialized integration for Santa Clara County (Silicon Valley)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config["jurisdiction_name"] = "Santa Clara County"
        super().__init__(jurisdiction_id, config)


# Legacy API for Secretary of State records
class CaliforniaSecretaryOfStateAPI(BaseAPIIntegration, APIKeyAuthentication):
    """
    Integration with California Secretary of State APIs
    Provides access to business filings, corporate records, and public documents
    """

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        # California SOS API endpoints
        self.base_url = "https://www.sos.ca.gov/api"

        # Available endpoints
        self.available_features = [
            "business_search",
            "corporate_filings",
            "lien_search",
            "trademark_search",
            "notary_search",
        ]

        logger.info("Initialized California Secretary of State API")

    def authenticate(self) -> bool:
        """Authenticate with California SOS API"""
        return super().authenticate()

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for business/corporate records using California SOS API"""
        if "business_search" not in self.available_features:
            logger.warning("Business search not available")
            return []

        try:
            search_type = self._determine_search_type(query)

            if search_type == "entity":
                return self._search_by_entity_number(query)
            elif search_type == "business":
                return self._search_businesses(query)
            else:
                results = []
                results.extend(self._search_businesses(query))
                results.extend(self._search_liens(query))
                return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _determine_search_type(self, query: Dict[str, Any]) -> str:
        """Determine the type of search to perform"""
        if query.get("entity_number"):
            return "entity"
        elif query.get("business_name") or query.get("owner_name"):
            return "business"
        elif query.get("lien_type"):
            return "lien"
        else:
            return "general"

    def _search_businesses(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for businesses and corporations"""
        try:
            search_params = {
                "business_name": query.get("business_name", ""),
                "owner_name": query.get("owner_name", ""),
                "status": query.get("status", ""),
                "filing_type": query.get("filing_type", ""),
            }
            search_params = {k: v for k, v in search_params.items() if v}

            response = self.make_request("GET", "business-search", params=search_params)
            data = self.validate_response(response)

            businesses = data.get("businesses", [])
            return [self._map_business_to_standard_format(biz) for biz in businesses]

        except Exception as e:
            logger.error(f"Business search failed: {e}")
            return []

    def _search_by_entity_number(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for specific entity by number"""
        entity_number = query.get("entity_number")
        if not entity_number:
            return []

        try:
            response = self.make_request("GET", f"entity/{entity_number}")
            data = self.validate_response(response)

            if data:
                return [self._map_business_to_standard_format(data)]
            return []

        except Exception as e:
            logger.error(f"Entity search failed for {entity_number}: {e}")
            return []

    def _search_liens(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for UCC filings and liens"""
        try:
            search_params = {
                "debtor_name": query.get("debtor_name", ""),
                "secured_party": query.get("secured_party", ""),
                "filing_type": query.get("lien_type", ""),
            }
            search_params = {k: v for k, v in search_params.items() if v}

            response = self.make_request("GET", "ucc-filings", params=search_params)
            data = self.validate_response(response)

            liens = data.get("filings", [])
            return [self._map_lien_to_standard_format(lien) for lien in liens]

        except Exception as e:
            logger.error(f"Lien search failed: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed business/corporate information"""
        try:
            response = self.make_request("GET", f"entity/{record_id}")
            data = self.validate_response(response)
            return self._map_business_to_standard_format(data)

        except Exception as e:
            logger.error(f"Failed to get details for record {record_id}: {e}")
            return {}

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_business_to_standard_format(api_data)

    def _map_business_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map California business data to DataGod standard format"""
        return {
            "record_type": "business",
            "record_id": f"CA-{api_data.get('entity_number', 'UNKNOWN')}",
            "title": api_data.get("entity_name", "Unknown Business"),
            "grantor": "",
            "grantee": api_data.get("entity_name", ""),
            "amount": 0.0,
            "address": api_data.get("address", ""),
            "city": api_data.get("city", ""),
            "state": "CA",
            "zip_code": api_data.get("zip_code", ""),
            "date": api_data.get("formation_date"),
            "status": api_data.get("status", "active"),
            "raw_data": api_data,
            "data_source": "california_sos_api",
            "scraped_at": datetime.now().isoformat(),
        }

    def _map_lien_to_standard_format(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map California lien/filing data to standard format"""
        return {
            "record_type": "ucc",
            "record_id": f"CA-LIEN-{api_data.get('filing_number', 'UNKNOWN')}",
            "title": f"UCC Filing - {api_data.get('debtor_name', 'Unknown')}",
            "grantor": api_data.get("debtor_name", ""),
            "grantee": api_data.get("secured_party", ""),
            "amount": float(api_data.get("amount", 0)),
            "address": api_data.get("debtor_address", ""),
            "date": api_data.get("filing_date"),
            "status": api_data.get("status", "active"),
            "raw_data": api_data,
            "data_source": "california_sos_ucc_api",
            "scraped_at": datetime.now().isoformat(),
        }
