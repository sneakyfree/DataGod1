"""
Illinois County Records API Integration
Integrates with Illinois county assessor and recorder APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class IllinoisCountyAPI(BaseAPIIntegration):
    """
    Integration with Illinois County Assessor and Recorder APIs
    Supports Cook County and other major Illinois counties
    """

    COUNTY_APIS = {
        'cook': {
            'base_url': 'https://www.cookcountyassessor.com/api',
            'recorder_url': 'https://www.cookcountyrecorder.com/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info', 'appeals']
        },
        'dupage': {
            'base_url': 'https://www.dupageco.org/api/assessor',
            'recorder_url': 'https://www.dupageco.org/api/recorder',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'lake': {
            'base_url': 'https://www.lakecountyil.gov/api/assessor',
            'recorder_url': 'https://www.lakecountyil.gov/api/recorder',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'will': {
            'base_url': 'https://www.willcountylandrecords.com/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'kane': {
            'base_url': 'https://www.kanecountyil.gov/api/assessor',
            'features': ['property_search', 'deed_records']
        },
        'mchenry': {
            'base_url': 'https://www.mchenrycountyil.gov/api/assessor',
            'features': ['property_search', 'deed_records']
        },
        'winnebago': {
            'base_url': 'https://www.wincoil.us/api/assessor',
            'features': ['property_search', 'deed_records']
        },
        'madison': {
            'base_url': 'https://www.co.madison.il.us/api/assessor',
            'features': ['property_search', 'deed_records']
        },
        'st-clair': {
            'base_url': 'https://www.co.st-clair.il.us/api/assessor',
            'features': ['property_search', 'deed_records']
        },
        'champaign': {
            'base_url': 'https://www.co.champaign.il.us/api/assessor',
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
            logger.warning(f"No specific API config for IL county: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}countyil.gov/api/assessor"
            self.recorder_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Illinois API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(' county'):
            name = name[:-7]
        return name.replace(' ', '-')

    def authenticate(self) -> bool:
        """Authenticate with Illinois API"""
        if self.api_key:
            logger.info("IL API key authentication configured")
            return True
        logger.info("Using public access for IL records")
        return True

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for property and deed records"""
        results = []

        if 'property_search' in self.available_features:
            results.extend(self._search_property_records(query))

        if 'deed_records' in self.available_features:
            results.extend(self._search_deed_records(query))

        if 'mortgage_records' in self.available_features:
            results.extend(self._search_mortgage_records(query))

        return results

    def _search_property_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search property assessment records"""
        try:
            params = {
                'pin': query.get('pin', ''),  # Property Index Number
                'address': query.get('address', ''),
                'owner': query.get('owner_name', ''),
                'city': query.get('city', ''),
                'township': query.get('township', '')
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
        """Search deed records from county recorder"""
        if not self.recorder_url:
            return []

        try:
            params = {
                'grantor': query.get('grantor', ''),
                'grantee': query.get('grantee', ''),
                'doc_type': query.get('doc_type', 'WARRANTY DEED'),
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

    def _search_mortgage_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search mortgage records"""
        if not self.recorder_url or 'mortgage_records' not in self.available_features:
            return []

        try:
            params = {
                'mortgagor': query.get('borrower', query.get('mortgagor', '')),
                'mortgagee': query.get('lender', query.get('mortgagee', '')),
                'doc_type': 'MORTGAGE',
                'date_from': query.get('date_from', ''),
                'date_to': query.get('date_to', '')
            }
            params = {k: v for k, v in params.items() if v}

            original_url = self.base_url
            self.base_url = self.recorder_url

            response = self.make_request('GET', 'documents/search', params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            mortgages = data.get('documents', [])
            return [self._map_mortgage_to_standard(m) for m in mortgages]

        except Exception as e:
            logger.error(f"Mortgage search failed for {self.county_name}: {e}")
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
        """Map Illinois property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('pin') or data.get('property_index_number'),
            'title': f"Property - {data.get('address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('taxpayer_name', data.get('owner_name', '')),
            'amount': float(data.get('assessed_value', 0)),
            'address': data.get('address', ''),
            'city': data.get('city', ''),
            'state': 'IL',
            'zip_code': data.get('zip_code', ''),
            'pin': data.get('pin', ''),
            'township': data.get('township', ''),
            'date': data.get('assessment_year'),
            'description': data.get('property_class_description', ''),
            'land_value': float(data.get('land_assessed', 0)),
            'building_value': float(data.get('building_assessed', 0)),
            'raw_data': data,
            'data_source': f'illinois_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Illinois deed record to standard format"""
        return {
            'record_type': data.get('doc_type', 'deed').lower().replace(' ', '_'),
            'record_id': data.get('document_number'),
            'title': f"{data.get('doc_type', 'Warranty Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('consideration', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'IL',
            'pin': data.get('pin', ''),
            'date': data.get('recording_date'),
            'document_number': data.get('document_number'),
            'raw_data': data,
            'data_source': f'illinois_{self.county_name}_recorder',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map mortgage record to standard format"""
        return {
            'record_type': 'mortgage',
            'record_id': data.get('document_number'),
            'title': f"Mortgage - {data.get('mortgagor', 'Unknown')}",
            'grantor': data.get('mortgagor', ''),
            'grantee': data.get('mortgagee', ''),
            'borrower': data.get('mortgagor', ''),
            'lender': data.get('mortgagee', ''),
            'amount': float(data.get('loan_amount', 0)),
            'date': data.get('recording_date'),
            'document_number': data.get('document_number'),
            'pin': data.get('pin', ''),
            'raw_data': data,
            'data_source': f'illinois_{self.county_name}_mortgage',
            'scraped_at': datetime.now().isoformat()
        }


class CookCountyAPI(IllinoisCountyAPI):
    """Specialized integration for Cook County (Chicago)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Cook County'
        super().__init__(jurisdiction_id, config)

    def get_assessment_appeal_info(self, pin: str) -> Dict[str, Any]:
        """Get assessment appeal information (Cook specific)"""
        if 'appeals' not in self.available_features:
            return {}

        try:
            response = self.make_request('GET', f'properties/{pin}/appeals')
            data = self.validate_response(response)
            return {
                'appeal_status': data.get('status'),
                'appeal_deadline': data.get('deadline'),
                'appeal_history': data.get('history', []),
                'board_of_review_value': float(data.get('bor_value', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get appeal info: {e}")
            return {}

    def get_tax_bill_info(self, pin: str) -> Dict[str, Any]:
        """Get tax bill details (Cook specific)"""
        if 'tax_info' not in self.available_features:
            return {}

        try:
            response = self.make_request('GET', f'properties/{pin}/tax-bill')
            data = self.validate_response(response)
            return {
                'tax_year': data.get('tax_year'),
                'first_installment': float(data.get('first_installment', 0)),
                'second_installment': float(data.get('second_installment', 0)),
                'total_tax': float(data.get('total_tax', 0)),
                'exemptions': data.get('exemptions', []),
                'payment_status': data.get('payment_status')
            }
        except Exception as e:
            logger.error(f"Failed to get tax bill: {e}")
            return {}


class DuPageCountyAPI(IllinoisCountyAPI):
    """Specialized integration for DuPage County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'DuPage County'
        super().__init__(jurisdiction_id, config)


class LakeCountyILAPI(IllinoisCountyAPI):
    """Specialized integration for Lake County, IL"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Lake County'
        super().__init__(jurisdiction_id, config)


class WillCountyAPI(IllinoisCountyAPI):
    """Specialized integration for Will County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Will County'
        super().__init__(jurisdiction_id, config)
