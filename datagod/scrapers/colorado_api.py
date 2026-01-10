"""
Colorado County Records API Integration
Integrates with Colorado county assessor and recorder APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class ColoradoCountyAPI(BaseAPIIntegration):
    """
    Integration with Colorado County Assessor and Clerk & Recorder APIs
    Supports Denver, El Paso, Arapahoe, Jefferson, Adams and other major counties
    """

    COUNTY_APIS = {
        'denver': {
            'base_url': 'https://www.denvergov.org/property/api',
            'recorder_url': 'https://www.denvergov.org/recorder/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info']
        },
        'el-paso': {
            'base_url': 'https://assessor.elpasoco.com/api',
            'recorder_url': 'https://car.elpasoco.com/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'arapahoe': {
            'base_url': 'https://www.arapahoegov.com/assessor/api',
            'recorder_url': 'https://www.arapahoegov.com/clerk/api',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'jefferson': {
            'base_url': 'https://www.jeffco.us/assessor/api',
            'recorder_url': 'https://www.jeffco.us/clerk/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'adams': {
            'base_url': 'https://www.adcogov.org/assessor/api',
            'recorder_url': 'https://www.adcogov.org/clerkrecorder/api',
            'features': ['property_search', 'deed_records']
        },
        'douglas': {
            'base_url': 'https://www.douglas.co.us/assessor/api',
            'features': ['property_search', 'tax_info']
        },
        'boulder': {
            'base_url': 'https://www.bouldercounty.org/assessor/api',
            'recorder_url': 'https://www.bouldercounty.org/clerk/api',
            'features': ['property_search', 'deed_records']
        },
        'larimer': {
            'base_url': 'https://www.larimer.org/assessor/api',
            'features': ['property_search', 'deed_records']
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
            logger.warning(f"No specific API config for Colorado county: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}county.com/assessor/api"
            self.recorder_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Colorado API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(' county'):
            name = name[:-7]
        return name.replace(' ', '-')

    def authenticate(self) -> bool:
        """Colorado APIs typically use API key authentication"""
        if self.api_key:
            logger.info("API key authentication configured")
            return True
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
                'schedule': query.get('property_id', ''),
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
        """Search deed/mortgage records from clerk & recorder"""
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
        """Map Colorado property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('schedule_number') or data.get('parcel_id'),
            'title': f"Property - {data.get('situs_address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('owner_name', ''),
            'amount': float(data.get('actual_value', 0) or data.get('assessed_value', 0)),
            'address': data.get('situs_address', ''),
            'city': data.get('city', ''),
            'state': 'CO',
            'zip_code': data.get('zip_code', ''),
            'date': data.get('assessment_date'),
            'description': data.get('legal_description', ''),
            'raw_data': data,
            'data_source': f'colorado_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Colorado deed record to standard format"""
        return {
            'record_type': data.get('document_type', 'deed').lower(),
            'record_id': data.get('reception_number') or data.get('document_number'),
            'title': f"{data.get('document_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('consideration', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'CO',
            'date': data.get('recording_date') or data.get('filed_date'),
            'document_number': data.get('reception_number'),
            'book_page': f"{data.get('book', '')}/{data.get('page', '')}",
            'raw_data': data,
            'data_source': f'colorado_{self.county_name}_recorder',
            'scraped_at': datetime.now().isoformat()
        }


class DenverCountyAPI(ColoradoCountyAPI):
    """Specialized integration for Denver County (City and County of Denver)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Denver County'
        super().__init__(jurisdiction_id, config)

    def get_building_permits(self, address: str) -> List[Dict[str, Any]]:
        """Get building permits for an address (Denver specific)"""
        try:
            response = self.make_request('GET', 'permits/search', params={'address': address})
            data = self.validate_response(response)
            return data.get('permits', [])
        except Exception as e:
            logger.error(f"Failed to get building permits: {e}")
            return []


class ElPasoCountyAPI(ColoradoCountyAPI):
    """Specialized integration for El Paso County (Colorado Springs)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'El Paso County'
        super().__init__(jurisdiction_id, config)


class ArapahoeCountyAPI(ColoradoCountyAPI):
    """Specialized integration for Arapahoe County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Arapahoe County'
        super().__init__(jurisdiction_id, config)


class JeffersonCountyAPI(ColoradoCountyAPI):
    """Specialized integration for Jefferson County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Jefferson County'
        super().__init__(jurisdiction_id, config)
