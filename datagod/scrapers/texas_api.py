"""
Texas County Records API Integration
Integrates with Texas county appraisal district and clerk APIs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from datagod.scrapers.base_api_integration import BaseAPIIntegration

logger = logging.getLogger(__name__)


class TexasCountyAPI(BaseAPIIntegration):
    """
    Integration with Texas County Appraisal District APIs
    Supports Harris, Dallas, Tarrant, Bexar, Travis and other major counties
    """

    COUNTY_APIS = {
        'harris': {
            'base_url': 'https://publicdata.hcad.org/api',
            'clerk_url': 'https://www.cclerk.hctx.net/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'tax_info']
        },
        'dallas': {
            'base_url': 'https://www.dallascad.org/api',
            'clerk_url': 'https://www.dallascounty.org/clerk/api',
            'features': ['property_search', 'deed_records', 'ucc_filings']
        },
        'tarrant': {
            'base_url': 'https://www.tad.org/api',
            'clerk_url': 'https://www.tarrantcounty.com/clerk/api',
            'features': ['property_search', 'deed_records', 'tax_info']
        },
        'bexar': {
            'base_url': 'https://www.bcad.org/api',
            'clerk_url': 'https://www.bexar.org/clerk/api',
            'features': ['property_search', 'deed_records', 'mortgage_records']
        },
        'travis': {
            'base_url': 'https://www.traviscad.org/api',
            'clerk_url': 'https://www.traviscountyclerk.org/api',
            'features': ['property_search', 'deed_records', 'mortgage_records', 'ucc_filings']
        },
        'collin': {
            'base_url': 'https://www.collincad.org/api',
            'features': ['property_search', 'tax_info']
        },
        'denton': {
            'base_url': 'https://www.dentoncad.com/api',
            'features': ['property_search', 'deed_records']
        },
        'fort-bend': {
            'base_url': 'https://www.fbcad.org/api',
            'features': ['property_search', 'tax_info']
        },
        'el-paso': {
            'base_url': 'https://www.epcad.org/api',
            'features': ['property_search', 'deed_records']
        },
        'hidalgo': {
            'base_url': 'https://www.hidalgoad.org/api',
            'features': ['property_search']
        }
    }

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        super().__init__(jurisdiction_id, config)

        self.county_name = self._extract_county_name(config.get('jurisdiction_name', ''))
        self.county_config = self.COUNTY_APIS.get(self.county_name.lower().replace(' ', '-'), {})

        if self.county_config:
            self.base_url = self.county_config.get('base_url', '')
            self.clerk_url = self.county_config.get('clerk_url', '')
            self.available_features = self.county_config.get('features', [])
        else:
            logger.warning(f"No specific API config for Texas county: {self.county_name}")
            self.base_url = f"https://www.{self.county_name.lower()}cad.org/api"
            self.clerk_url = ''
            self.available_features = ['property_search']

        logger.info(f"Initialized Texas API for {self.county_name} County")

    def _extract_county_name(self, jurisdiction_name: str) -> str:
        """Extract county name from jurisdiction name"""
        name = jurisdiction_name.lower()
        if name.endswith(' county'):
            name = name[:-7]
        return name.replace(' ', '-')

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for property and deed records"""
        results = []

        # Search property records
        if 'property_search' in self.available_features:
            results.extend(self._search_property_records(query))

        # Search deed records
        if 'deed_records' in self.available_features:
            results.extend(self._search_deed_records(query))

        return results

    def _search_property_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search property appraisal records"""
        try:
            params = {
                'account': query.get('property_id', ''),
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
        """Search deed/mortgage records from county clerk"""
        if not self.clerk_url:
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

            # Use clerk URL for deed records
            original_url = self.base_url
            self.base_url = self.clerk_url

            response = self.make_request('GET', 'records/search', params=params)
            data = self.validate_response(response)

            self.base_url = original_url

            records = data.get('records', data.get('documents', []))
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

    def get_mortgage_records(self, property_id: str) -> List[Dict[str, Any]]:
        """Get mortgage records for a property"""
        if 'mortgage_records' not in self.available_features:
            return []

        try:
            response = self.make_request('GET', f'properties/{property_id}/mortgages')
            data = self.validate_response(response)

            mortgages = data.get('mortgages', [])
            return [self._map_mortgage_to_standard(m) for m in mortgages]

        except Exception as e:
            logger.error(f"Failed to get mortgages for {property_id}: {e}")
            return []

    def _map_property_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Texas property data to standard format"""
        return {
            'record_type': 'property',
            'record_id': data.get('account_number') or data.get('property_id'),
            'title': f"Property - {data.get('situs_address', 'Unknown Address')}",
            'grantor': '',
            'grantee': data.get('owner_name', ''),
            'amount': float(data.get('market_value', 0)),
            'address': data.get('situs_address', ''),
            'city': data.get('city', ''),
            'state': 'TX',
            'zip_code': data.get('zip_code', ''),
            'date': data.get('certification_date'),
            'description': data.get('legal_description', ''),
            'raw_data': data,
            'data_source': f'texas_{self.county_name}_api',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_deed_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Texas deed record to standard format"""
        return {
            'record_type': data.get('document_type', 'deed').lower(),
            'record_id': data.get('document_number') or data.get('instrument_number'),
            'title': f"{data.get('document_type', 'Deed')} - {data.get('grantor', 'Unknown')}",
            'grantor': data.get('grantor', ''),
            'grantee': data.get('grantee', ''),
            'amount': float(data.get('consideration', 0)),
            'address': data.get('property_address', ''),
            'city': data.get('city', ''),
            'state': 'TX',
            'date': data.get('recording_date') or data.get('filed_date'),
            'document_number': data.get('document_number'),
            'book_page': f"{data.get('book', '')}/{data.get('page', '')}",
            'raw_data': data,
            'data_source': f'texas_{self.county_name}_clerk',
            'scraped_at': datetime.now().isoformat()
        }

    def _map_mortgage_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map mortgage record to standard format"""
        return {
            'record_type': 'mortgage',
            'record_id': data.get('document_number'),
            'title': f"Mortgage - {data.get('borrower', 'Unknown')}",
            'grantor': data.get('borrower', ''),
            'grantee': data.get('lender', ''),
            'borrower': data.get('borrower', ''),
            'lender': data.get('lender', ''),
            'amount': float(data.get('loan_amount', 0)),
            'date': data.get('recording_date'),
            'document_number': data.get('document_number'),
            'raw_data': data,
            'data_source': f'texas_{self.county_name}_mortgage',
            'scraped_at': datetime.now().isoformat()
        }


class HarrisCountyAPI(TexasCountyAPI):
    """Specialized integration for Harris County (Houston)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Harris County'
        super().__init__(jurisdiction_id, config)

    def get_flood_zone_info(self, property_id: str) -> Dict[str, Any]:
        """Get flood zone information (Harris specific)"""
        try:
            response = self.make_request('GET', f'properties/{property_id}/flood')
            data = self.validate_response(response)
            return {
                'flood_zone': data.get('zone_designation'),
                'flood_risk': data.get('risk_level'),
                'base_flood_elevation': data.get('bfe'),
                'in_floodway': data.get('in_floodway', False)
            }
        except Exception as e:
            logger.error(f"Failed to get flood info: {e}")
            return {}


class DallasCountyAPI(TexasCountyAPI):
    """Specialized integration for Dallas County"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Dallas County'
        super().__init__(jurisdiction_id, config)

    def get_ucc_filings(self, debtor_name: str) -> List[Dict[str, Any]]:
        """Get UCC filings for a debtor"""
        if 'ucc_filings' not in self.available_features:
            return []

        try:
            response = self.make_request('GET', 'ucc/search', params={'debtor': debtor_name})
            data = self.validate_response(response)

            filings = data.get('filings', [])
            return [self._map_ucc_to_standard(f) for f in filings]
        except Exception as e:
            logger.error(f"Failed to get UCC filings: {e}")
            return []

    def _map_ucc_to_standard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map UCC filing to standard format"""
        return {
            'record_type': 'ucc',
            'record_id': data.get('filing_number'),
            'title': f"UCC Filing - {data.get('debtor_name', 'Unknown')}",
            'grantor': data.get('debtor_name', ''),
            'grantee': data.get('secured_party', ''),
            'amount': float(data.get('collateral_value', 0)),
            'date': data.get('filing_date'),
            'document_number': data.get('filing_number'),
            'description': data.get('collateral_description', ''),
            'raw_data': data,
            'data_source': 'texas_dallas_ucc',
            'scraped_at': datetime.now().isoformat()
        }


class TravisCountyAPI(TexasCountyAPI):
    """Specialized integration for Travis County (Austin)"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        config['jurisdiction_name'] = 'Travis County'
        super().__init__(jurisdiction_id, config)
