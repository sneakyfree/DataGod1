"""
Pennsylvania County Records API Integration
Integrates with Pennsylvania county recorder and assessment APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class PennsylvaniaCountyAPI(BaseAPIIntegration):
    """
    Integration with Pennsylvania County Recorder and Assessment APIs
    Supports Philadelphia and other major PA counties
    """

    COUNTY_APIS = {
        'philadelphia': {
            'base_url': 'https://property.phila.gov/api',
            'recorder_url': 'https://epay.phila-records.com/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info', 'permits']
        },
        'allegheny': {  # Pittsburgh
            'base_url': 'https://www2.alleghenycounty.us/api/assessment',
            'recorder_url': 'https://www2.alleghenycounty.us/api/recorder',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info']
        },
        'montgomery': {
            'base_url': 'https://www.montcopa.org/api/assessment',
            'recorder_url': 'https://www.montcopa.org/api/recorder',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'bucks': {
            'base_url': 'https://www.buckscounty.org/api/assessment',
            'recorder_url': 'https://www.buckscounty.org/api/recorder',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'delaware': {
            'base_url': 'https://www.delcopa.gov/api/assessment',
            'recorder_url': 'https://www.delcopa.gov/api/recorder',
            'features': ['property_search', 'deed_records']
        },
        'chester': {
            'base_url': 'https://www.chesco.org/api/assessment',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'lancaster': {
            'base_url': 'https://www.co.lancaster.pa.us/api/assessment',
            'features': ['property_search', 'deed_records']
        },
        'york': {
            'base_url': 'https://www.yorkcountypa.gov/api/assessment',
            'features': ['property_search', 'deed_records']
        },
        'berks': {
            'base_url': 'https://www.co.berks.pa.us/api/assessment',
            'features': ['property_search', 'deed_records']
        },
        'lehigh': {
            'base_url': 'https://www.lehighcounty.org/api/assessment',
            'features': ['property_search', 'deed_records']
        },
        'northampton': {
            'base_url': 'https://www.northamptoncounty.org/api/assessment',
            'features': ['property_search', 'deed_records']
        },
        'dauphin': {  # Harrisburg
            'base_url': 'https://www.dauphincounty.org/api/assessment',
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
            logger.warning(f"No specific API config for PA county: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}countypa.gov/api/assessment"
            self.recorder_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Pennsylvania API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(' county'):
            name = name[:-7]
        return name.replace(' ', '-')

    def authenticate(self) -> bool:
        """Authenticate with Pennsylvania API"""
        if self.api_key:
            logger.info("PA API key authentication configured")
            return True
        logger.info("Using public access for PA records")
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
                'parcel_id': query.get('parcel_id', ''),
                'address': query.get('address', ''),
                'owner': query.get('owner_name', ''),
                'city': query.get('city', ''),
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
        """Search deed records from county recorder"""
        if not self.recorder_url:
            return []

        try:
            params = {
                'grantor': query.get('grantor', ''),
                'grantee': query.get('grantee', ''),
                'doc_type': query.get('doc_type', 'DEED'),
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
        """Map Pennsylvania property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('parcel_id') or data.get('opa_number'),
            'title': f"Property - {data.get('address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('owner_name', ''),
            'amount': float(data.get('market_value', 0)),
            'address': data.get('address', ''),
            'city': data.get('city', ''),
            'state': 'PA',
            'zip_code': data.get('zip_code', ''),
            'parcel_id': data.get('parcel_id', ''),
            'date': data.get('assessment_date'),
            'description': data.get('category_code_description', ''),
            'land_value': float(data.get('land_value', 0)),
            'improvement_value': float(data.get('improvement_value', 0)),
            'raw_data': data,
            'data_source': f'pennsylvania_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Pennsylvania deed record to standard format"""
        return {
            'record_type': data.get('doc_type', 'deed').lower(),
            'record_id': data.get('document_number') or data.get('instrument_number'),
            'title': f"{data.get('doc_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('consideration', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'PA',
            'parcel_id': data.get('parcel_id', ''),
            'date': data.get('recording_date'),
            'document_number': data.get('document_number'),
            'book_page': f"{data.get('book', '')}/{data.get('page', '')}",
            'raw_data': data,
            'data_source': f'pennsylvania_{self.county_name}_recorder',
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
            'parcel_id': data.get('parcel_id', ''),
            'raw_data': data,
            'data_source': f'pennsylvania_{self.county_name}_mortgage',
            'scraped_at': datetime.now().isoformat()
        }


class PhiladelphiaCountyAPI(PennsylvaniaCountyAPI):
    """Specialized integration for Philadelphia County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Philadelphia County'
        super().__init__(jurisdiction_id, config)

    def get_permit_history(self, opa_number: str) -> List[Dict[str, Any]]:
        """Get building permit history (Philadelphia specific)"""
        if 'permits' not in self.available_features:
            return []

        try:
            response = self.make_request('GET', f'properties/{opa_number}/permits')
            data = self.validate_response(response)

            permits = data.get('permits', [])
            return [{
                'permit_number': p.get('permit_number'),
                'permit_type': p.get('permit_type'),
                'issue_date': p.get('issue_date'),
                'status': p.get('status'),
                'description': p.get('description')
            } for p in permits]

        except Exception as e:
            logger.error(f"Failed to get permits: {e}")
            return []

    def get_tax_delinquency_info(self, opa_number: str) -> Dict[str, Any]:
        """Get tax delinquency information (Philadelphia specific)"""
        if 'tax_info' not in self.available_features:
            return {}

        try:
            response = self.make_request('GET', f'properties/{opa_number}/tax-status')
            data = self.validate_response(response)
            return {
                'is_delinquent': data.get('is_delinquent', False),
                'total_due': float(data.get('total_due', 0)),
                'years_delinquent': data.get('years_delinquent', []),
                'payment_agreement': data.get('payment_agreement_active', False)
            }
        except Exception as e:
            logger.error(f"Failed to get tax delinquency: {e}")
            return {}


class AlleghenyCountyAPI(PennsylvaniaCountyAPI):
    """Specialized integration for Allegheny County (Pittsburgh)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Allegheny County'
        super().__init__(jurisdiction_id, config)

    def get_clean_and_green_info(self, parcel_id: str) -> Dict[str, Any]:
        """Get Clean and Green (agricultural) tax status"""
        if 'tax_info' not in self.available_features:
            return {}

        try:
            response = self.make_request('GET', f'properties/{parcel_id}/clean-green')
            data = self.validate_response(response)
            return {
                'enrolled': data.get('enrolled', False),
                'program_type': data.get('program_type'),
                'acreage': float(data.get('acreage', 0)),
                'preferential_assessment': float(data.get('preferential_assessment', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get clean and green info: {e}")
            return {}


class MontgomeryCountyPAAPI(PennsylvaniaCountyAPI):
    """Specialized integration for Montgomery County, PA"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Montgomery County'
        super().__init__(jurisdiction_id, config)


class BucksCountyAPI(PennsylvaniaCountyAPI):
    """Specialized integration for Bucks County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Bucks County'
        super().__init__(jurisdiction_id, config)
