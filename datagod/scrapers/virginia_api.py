"""
Virginia County Records API Integration
Integrates with Virginia county assessor and circuit court APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class VirginiaCountyAPI(BaseAPIIntegration):
    """
    Integration with Virginia County Assessor and Circuit Court APIs
    Supports Fairfax, Virginia Beach, Prince William, Loudoun, Chesterfield and other major jurisdictions
    Note: Virginia has independent cities that function separately from counties
    """

    COUNTY_APIS = {
        'fairfax': {
            'base_url': 'https://www.fairfaxcounty.gov/propertyinfo/api',
            'circuit_url': 'https://www.fairfaxcounty.gov/circuit/landrecords/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info']
        },
        'virginia-beach': {
            'base_url': 'https://www.vbgov.com/assessor/api',
            'circuit_url': 'https://www.vbgov.com/courts/circuit/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'prince-william': {
            'base_url': 'https://www.pwcgov.org/assessor/api',
            'circuit_url': 'https://www.pwcgov.org/circuit/api',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'loudoun': {
            'base_url': 'https://www.loudoun.gov/assessor/api',
            'circuit_url': 'https://www.loudoun.gov/courts/circuit/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'chesterfield': {
            'base_url': 'https://www.chesterfield.gov/realestate/api',
            'circuit_url': 'https://www.chesterfield.gov/courts/api',
            'features': ['property_search', 'deed_records']
        },
        'henrico': {
            'base_url': 'https://www.henrico.us/assessor/api',
            'features': ['property_search', 'tax_info']
        },
        'norfolk': {
            'base_url': 'https://www.norfolk.gov/assessor/api',
            'circuit_url': 'https://www.norfolk.gov/circuit/api',
            'features': ['property_search', 'deed_records']
        },
        'chesapeake': {
            'base_url': 'https://www.cityofchesapeake.net/assessor/api',
            'features': ['property_search', 'deed_records']
        }
    }

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        self.county_name = self._extract_county_name(config.get('jurisdiction_name', ''))
        self.county_config = self.COUNTY_APIS.get(self.county_name.lower().replace(' ', '-'), {})

        if self.county_config:
            self.base_url = self.county_config.get('base_url', '')
            self.circuit_url = self.county_config.get('circuit_url', '')
            self.available_features = self.county_config.get('features', [])
        else:
            logger.warning(f"No specific API config for Virginia jurisdiction: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}va.gov/assessor/api"
            self.circuit_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Virginia API for {self.county_name}")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county/city name from jurisdiction name"""
        name = jurisdiction_name.lower()
        for suffix in [' county', ' city']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name.replace(' ', '-')

    def authenticate(self) -> bool:
        """Virginia APIs typically use API key authentication"""
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
        """Search deed/mortgage records from circuit court"""
        if not self.circuit_url:
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
            self.base_url = self.circuit_url

            response = self.make_request('GET', 'landrecords/search', params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            records = data.get('instruments', data.get('records', []))
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
        """Map Virginia property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('tax_map_number') or data.get('parcel_id'),
            'title': f"Property - {data.get('property_address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('owner_name', ''),
            'amount': float(data.get('total_value', 0) or data.get('assessed_value', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'VA',
            'zip_code': data.get('zip_code', ''),
            'date': data.get('last_sale_date'),
            'description': data.get('legal_description', ''),
            'raw_data': data,
            'data_source': f'virginia_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Virginia deed record to standard format"""
        return {
            'record_type': data.get('instrument_type', 'deed').lower(),
            'record_id': data.get('instrument_number') or data.get('document_number'),
            'title': f"{data.get('instrument_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('consideration', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'VA',
            'date': data.get('recording_date') or data.get('instrument_date'),
            'document_number': data.get('instrument_number'),
            'book_page': f"{data.get('book', '')}/{data.get('page', '')}",
            'raw_data': data,
            'data_source': f'virginia_{self.county_name}_circuit',
            'scraped_at': datetime.now().isoformat()
        }


class FairfaxCountyAPI(VirginiaCountyAPI):
    """Specialized integration for Fairfax County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Fairfax County'
        super().__init__(jurisdiction_id, config)

    def get_zoning_info(self, parcel_id: str) -> Dict[str, Any]:
        """Get zoning information for a parcel (Fairfax specific)"""
        try:
            response = self.make_request('GET', f'properties/{parcel_id}/zoning')
            data = self.validate_response(response)
            return {
                'zoning_district': data.get('zoning_district'),
                'zoning_description': data.get('description'),
                'overlay_districts': data.get('overlay_districts', []),
                'permitted_uses': data.get('permitted_uses', [])
            }
        except Exception as e:
            logger.error(f"Failed to get zoning info: {e}")
            return {}


class VirginiaBeachCityAPI(VirginiaCountyAPI):
    """Specialized integration for Virginia Beach (independent city)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Virginia Beach'
        super().__init__(jurisdiction_id, config)


class PrinceWilliamCountyAPI(VirginiaCountyAPI):
    """Specialized integration for Prince William County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Prince William County'
        super().__init__(jurisdiction_id, config)


class LoudounCountyAPI(VirginiaCountyAPI):
    """Specialized integration for Loudoun County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Loudoun County'
        super().__init__(jurisdiction_id, config)
