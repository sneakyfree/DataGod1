"""
Washington State County Records API Integration
Integrates with Washington county assessor and recorder APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class WashingtonCountyAPI(BaseAPIIntegration):
    """
    Integration with Washington County Assessor and Recorder APIs
    Supports King, Pierce, Snohomish, Clark, Spokane and other major counties
    """

    COUNTY_APIS = {
        'king': {
            'base_url': 'https://blue.kingcounty.com/Assessor/eRealProperty/api',
            'recorder_url': 'https://recordingsearch.kingcounty.gov/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info']
        },
        'pierce': {
            'base_url': 'https://www.co.pierce.wa.us/assessor/api',
            'recorder_url': 'https://www.co.pierce.wa.us/auditor/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'snohomish': {
            'base_url': 'https://www.snoco.org/assessor/api',
            'recorder_url': 'https://www.snoco.org/auditor/api',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'clark': {
            'base_url': 'https://gis.clark.wa.gov/assessor/api',
            'recorder_url': 'https://www.clark.wa.gov/auditor/api',
            'features': ['property_search', 'deed_records']
        },
        'spokane': {
            'base_url': 'https://www.spokanecounty.org/assessor/api',
            'recorder_url': 'https://www.spokanecounty.org/auditor/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'thurston': {
            'base_url': 'https://www.thurstoncountywa.gov/assessor/api',
            'features': ['property_search', 'tax_info']
        },
        'kitsap': {
            'base_url': 'https://www.kitsapgov.com/assessor/api',
            'features': ['property_search', 'deed_records']
        },
        'whatcom': {
            'base_url': 'https://www.whatcomcounty.us/assessor/api',
            'features': ['property_search']
        }
    }

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        self.county_name = self._extract_county_name(config.get('jurisdiction_name', ''))
        self.county_config = self.COUNTY_APIS.get(self.county_name.lower().replace(' ', '-'), {})

        if self.county_config:
            self.base_url = self.county_config.get('base_url', '')
            self.recorder_url = self.county_config.get('recorder_url', '')
            self.available_features = self.county_config.get('features', [])
        else:
            logger.warning(f"No specific API config for Washington county: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}countywa.gov/assessor/api"
            self.recorder_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Washington API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(' county'):
            name = name[:-7]
        return name.replace(' ', '-')

    def authenticate(self) -> bool:
        """Washington APIs typically use API key authentication"""
        if self.api_key:
            logger.info("API key authentication configured")
            return True
        # Many Washington county APIs are public
        logger.info("No authentication required for public API")
        return True

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for property and deed records"""
        results = []

        if 'property_search' in self.available_features:
            results.extend(self._search_property_records(query))

        if 'deed_records' in self.available_features:
            results.extend(self._search_deed_records(query))

        return results

    def _search_property_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search property assessment records"""
        try:
            params = {
                'parcel': query.get('property_id', ''),
                'owner': query.get('owner_name', ''),
                'address': query.get('address', ''),
                'zip': query.get('zip_code', '')
            }
            params = {k: v for k, v in params.items() if v}

            response = self.make_request('GET', 'properties/search', params=params)
            data = self.validate_response(response)

            properties = data.get('properties', data.get('results', []))
            return [self._map_property_to_standard(prop) for prop in properties]

        except Exception as e:
            logger.error(f"Property search failed for {self.county_name}: {e}")
            return []

    def _search_deed_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search deed/mortgage records from county auditor"""
        if not self.recorder_url:
            return []

        try:
            params = {
                'grantor': query.get('grantor', ''),
                'grantee': query.get('grantee', ''),
                'doc_type': query.get('record_type', 'DEED'),
                'date_from': query.get('date_from', ''),
                'date_to': query.get('date_to', '')
            }
            params = {k: v for k, v in params.items() if v}

            original_url = self.base_url
            self.base_url = self.recorder_url

            response = self.make_request('GET', 'documents/search', params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            records = data.get('documents', data.get('records', []))
            return [self._map_deed_to_standard(record) for record in records]

        except Exception as e:
            logger.error(f"Deed search failed for {self.county_name}: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed record information"""
        try:
            response = self.make_request('GET', f'properties/{record_id}')
            data = self.validate_response(response)
            return self._map_property_to_standard(data)
        except Exception as e:
            logger.error(f"Failed to get details for {record_id}: {e}")
            return {}

    def map_api_data_to_standard_format(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map API data to standard format"""
        return self._map_property_to_standard(api_data)

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Washington property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('parcel_number') or data.get('account_number'),
            'title': f"Property - {data.get('site_address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('owner_name', ''),
            'amount': float(data.get('assessed_value', 0) or data.get('market_value', 0)),
            'address': data.get('site_address', ''),
            'city': data.get('city', ''),
            'state': 'WA',
            'zip_code': data.get('zip_code', ''),
            'date': data.get('assessment_date'),
            'description': data.get('legal_description', ''),
            'raw_data': data,
            'data_source': f'washington_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Washington deed record to standard format"""
        return {
            'record_type': data.get('document_type', 'deed').lower(),
            'record_id': data.get('document_number') or data.get('afe_number'),
            'title': f"{data.get('document_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('excise_tax_paid', 0) * 100 / 1.28 if data.get('excise_tax_paid') else 0),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'WA',
            'date': data.get('recording_date') or data.get('filed_date'),
            'document_number': data.get('document_number'),
            'book_page': f"{data.get('book', '')}/{data.get('page', '')}",
            'raw_data': data,
            'data_source': f'washington_{self.county_name}_recorder',
            'scraped_at': datetime.now().isoformat()
        }


class KingCountyAPI(WashingtonCountyAPI):
    """Specialized integration for King County (Seattle)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'King County'
        super().__init__(jurisdiction_id, config)

    def get_parcel_details(self, parcel_number: str) -> Dict[str, Any]:
        """Get detailed parcel information (King specific)"""
        try:
            response = self.make_request('GET', f'parcels/{parcel_number}/details')
            data = self.validate_response(response)
            return {
                'parcel_number': data.get('parcel_number'),
                'land_value': data.get('land_value'),
                'improvement_value': data.get('improvement_value'),
                'total_value': data.get('total_value'),
                'year_built': data.get('year_built'),
                'square_footage': data.get('square_footage'),
                'bedrooms': data.get('bedrooms'),
                'bathrooms': data.get('bathrooms'),
                'zoning': data.get('zoning')
            }
        except Exception as e:
            logger.error(f"Failed to get parcel details: {e}")
            return {}


class PierceCountyAPI(WashingtonCountyAPI):
    """Specialized integration for Pierce County (Tacoma)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Pierce County'
        super().__init__(jurisdiction_id, config)


class SnohomishCountyAPI(WashingtonCountyAPI):
    """Specialized integration for Snohomish County (Everett)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Snohomish County'
        super().__init__(jurisdiction_id, config)
