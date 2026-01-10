"""
Vermont State API Integration
Auto-generated scraper for Vermont (VT) public records

Generated: 2025-12-31T17:39:32.346864
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from datagod.scrapers.base_api_integration import (
    BaseAPIIntegration,
    APIKeyAuthentication,
    OAuth2Authentication,
    HMACAuthentication,
    APIDataError,
    RateLimitExceeded
)

logger = logging.getLogger(__name__)


# County-specific API configurations
COUNTY_APIS = {
    'chittenden': {
        'name': 'Chittenden',
        'base_url': 'https://www.chittendencounty.gov/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
    'rutland': {
        'name': 'Rutland',
        'base_url': 'https://www.rutlandcounty.org/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
    'washington': {
        'name': 'Washington',
        'base_url': 'https://www.washingtoncountyvt.org/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
    'windsor': {
        'name': 'Windsor',
        'base_url': 'https://www.windsorcountyvt.gov/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
    'franklin': {
        'name': 'Franklin',
        'base_url': 'https://www.franklincountyvt.gov/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
    'addison': {
        'name': 'Addison',
        'base_url': 'https://www.addisoncountyvt.gov/recorder/api',
        'property_endpoint': '/property/search',
        'deed_endpoint': '/deed/search',
        'lien_endpoint': '/lien/search',
        'requires_auth': False,
        'rate_limit': 30,
    },
}


class VermontAPI(BaseAPIIntegration):
    """
    API integration for Vermont (VT) public records.

    Supports:
    - Property records search
    - Deed records search
    - Lien records search
    - Tax records search

    Counties covered: See COUNTY_APIS dictionary above.
    """

    STATE_CODE = 'VT'
    STATE_NAME = 'Vermont'

    # Default rate limits
    DEFAULT_REQUESTS_PER_MINUTE = 60
    DEFAULT_REQUESTS_PER_HOUR = 1000
    DEFAULT_TIMEOUT = 30

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any] = None):
        """
        Initialize the Vermont API integration.

        Args:
            jurisdiction_id: Database ID for this jurisdiction
            config: Optional configuration overrides
        """
        # Build default config
        default_config = {
            'base_url': config.get('base_url', '') if config else '',
            'requests_per_minute': self.DEFAULT_REQUESTS_PER_MINUTE,
            'requests_per_hour': self.DEFAULT_REQUESTS_PER_HOUR,
            'timeout': self.DEFAULT_TIMEOUT,
        }

        # Merge with provided config
        if config:
            default_config.update(config)

        super().__init__(jurisdiction_id, default_config)

        # Track which county we're querying
        self.current_county = None

        logger.info(f"Initialized {self.STATE_NAME} API for jurisdiction {jurisdiction_id}")

    def authenticate(self) -> bool:
        """
        Authenticate with the Vermont API.

        Returns:
            True if authentication successful
        """
        # Try parent class authentication first
        if hasattr(super(), 'authenticate'):
            return super().authenticate()

        # If no API key required, return True
        if not self.api_key:
            logger.info(f"{self.STATE_NAME} API does not require authentication")
            return True

        logger.info(f"{self.STATE_NAME} API key authentication configured")
        return True

    def set_county(self, county_name: str) -> bool:
        """
        Set the active county for queries.

        Args:
            county_name: Name of the county

        Returns:
            True if county is valid and configured
        """
        county_key = county_name.lower().replace(' ', '_').replace("'", "")

        if county_key not in COUNTY_APIS:
            logger.warning(f"County '{county_name}' not found in {self.STATE_NAME} configuration")
            return False

        self.current_county = county_key
        county_config = COUNTY_APIS[county_key]

        # Update base URL if county has specific URL
        if county_config.get('base_url'):
            self.base_url = county_config['base_url']

        logger.info(f"Set active county to {county_name}")
        return True

    def get_county_config(self, county_name: str = None) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific county."""
        if county_name:
            county_key = county_name.lower().replace(' ', '_').replace("'", "")
        else:
            county_key = self.current_county

        return COUNTY_APIS.get(county_key)

    def list_counties(self) -> List[str]:
        """List all supported counties."""
        return [config['name'] for config in COUNTY_APIS.values()]

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        Search for records across all record types.

        Args:
            query: Search parameters
                - name: Person or entity name
                - address: Property address
                - parcel_id: Parcel/APN number
                - date_from: Start date (YYYY-MM-DD)
                - date_to: End date (YYYY-MM-DD)
                - record_type: Specific record type to search
            **kwargs: Additional parameters
                - county: Specific county to search

        Returns:
            List of matching records
        """
        county = kwargs.get('county')
        if county:
            self.set_county(county)

        record_type = query.get('record_type', 'all')

        results = []

        if record_type in ('all', 'property'):
            results.extend(self.search_property(query))

        if record_type in ('all', 'deed'):
            results.extend(self.search_deeds(query))

        if record_type in ('all', 'lien'):
            results.extend(self.search_liens(query))

        logger.info(f"Search returned {len(results)} total records")
        return results

    def search_property(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search property records.

        Args:
            query: Search parameters

        Returns:
            List of property records
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning("No county configured for property search")
            return []

        endpoint = county_config.get('property_endpoint', '/property/search')

        # Build request parameters
        params = {}
        if query.get('name'):
            params['owner_name'] = query['name']
        if query.get('address'):
            params['property_address'] = query['address']
        if query.get('parcel_id'):
            params['parcel_number'] = query['parcel_id']

        try:
            response = self.make_request('GET', endpoint, params=params)
            data = self.validate_response(response)

            results = []
            for record in data.get('results', data.get('properties', [])):
                mapped = self.map_api_data_to_standard_format(record)
                mapped['record_type'] = 'property'
                mapped['source_county'] = county_config['name']
                results.append(mapped)

            logger.info(f"Property search returned {len(results)} records")
            return results

        except Exception as e:
            logger.error(f"Property search failed: {e}")
            return []

    def search_deeds(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search deed records.

        Args:
            query: Search parameters

        Returns:
            List of deed records
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning("No county configured for deed search")
            return []

        endpoint = county_config.get('deed_endpoint', '/deed/search')

        # Build request parameters
        params = {}
        if query.get('name'):
            params['party_name'] = query['name']
        if query.get('date_from'):
            params['start_date'] = query['date_from']
        if query.get('date_to'):
            params['end_date'] = query['date_to']
        if query.get('document_number'):
            params['doc_number'] = query['document_number']

        try:
            response = self.make_request('GET', endpoint, params=params)
            data = self.validate_response(response)

            results = []
            for record in data.get('results', data.get('deeds', [])):
                mapped = self.map_api_data_to_standard_format(record)
                mapped['record_type'] = 'deed'
                mapped['source_county'] = county_config['name']
                results.append(mapped)

            logger.info(f"Deed search returned {len(results)} records")
            return results

        except Exception as e:
            logger.error(f"Deed search failed: {e}")
            return []

    def search_liens(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search lien records.

        Args:
            query: Search parameters

        Returns:
            List of lien records
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning("No county configured for lien search")
            return []

        endpoint = county_config.get('lien_endpoint', '/lien/search')

        # Build request parameters
        params = {}
        if query.get('name'):
            params['debtor_name'] = query['name']
        if query.get('date_from'):
            params['filed_from'] = query['date_from']
        if query.get('date_to'):
            params['filed_to'] = query['date_to']

        try:
            response = self.make_request('GET', endpoint, params=params)
            data = self.validate_response(response)

            results = []
            for record in data.get('results', data.get('liens', [])):
                mapped = self.map_api_data_to_standard_format(record)
                mapped['record_type'] = 'lien'
                mapped['source_county'] = county_config['name']
                results.append(mapped)

            logger.info(f"Lien search returned {len(results)} records")
            return results

        except Exception as e:
            logger.error(f"Lien search failed: {e}")
            return []

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific record.

        Args:
            record_id: Unique record identifier

        Returns:
            Detailed record information
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning("No county configured for record details")
            return {}

        endpoint = f"/record/{record_id}"

        try:
            response = self.make_request('GET', endpoint)
            data = self.validate_response(response)

            return self.map_api_data_to_standard_format(data)

        except Exception as e:
            logger.error(f"Get record details failed: {e}")
            return {}

    def map_api_data_to_standard_format(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Vermont-specific API data to standard DataGod format.

        Args:
            api_data: Raw API response data

        Returns:
            Standardized record dictionary
        """
        # Standard field mappings - adjust based on actual API responses
        standard = {
            'source_state': self.STATE_CODE,
            'source_api': self.__class__.__name__,
            'raw_data': api_data,
            'fetched_at': datetime.now().isoformat(),
        }

        # Map common fields with various possible names
        field_mappings = {
            'record_id': ['id', 'record_id', 'document_id', 'doc_id', 'reference_number'],
            'document_number': ['document_number', 'doc_number', 'instrument_number', 'book_page'],
            'record_date': ['record_date', 'recorded_date', 'filing_date', 'date', 'date_recorded'],
            'document_type': ['document_type', 'doc_type', 'type', 'instrument_type'],
            'grantor': ['grantor', 'seller', 'from_party', 'party1'],
            'grantee': ['grantee', 'buyer', 'to_party', 'party2'],
            'property_address': ['property_address', 'address', 'situs_address', 'location'],
            'parcel_id': ['parcel_id', 'apn', 'parcel_number', 'tax_id', 'pin'],
            'amount': ['amount', 'consideration', 'value', 'sale_price', 'loan_amount'],
            'legal_description': ['legal_description', 'legal_desc', 'legal'],
        }

        for standard_field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in api_data and api_data[name]:
                    standard[standard_field] = api_data[name]
                    break

        # Parse amount to float if present
        if 'amount' in standard:
            try:
                amount_str = str(standard['amount']).replace('$', '').replace(',', '')
                standard['amount'] = float(amount_str)
            except (ValueError, TypeError):
                pass

        # Parse date if present
        if 'record_date' in standard:
            try:
                if isinstance(standard['record_date'], str):
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y%m%d', '%d-%m-%Y']:
                        try:
                            dt = datetime.strptime(standard['record_date'], fmt)
                            standard['record_date'] = dt.date().isoformat()
                            break
                        except ValueError:
                            continue
            except Exception:
                pass

        return standard

    
    def search_property(self, query: Dict[str, Any], county: str = None) -> List[Dict[str, Any]]:
        """Search property records."""
        endpoint = "/property/search"
        if county:
            county_config = self.COUNTY_APIS.get(county.lower().replace(' ', '_'))
            if county_config:
                endpoint = county_config.get('property_endpoint', endpoint)

        response = self.make_request('GET', endpoint, params=query)
        data = self.validate_response(response)

        results = []
        for record in data.get('results', []):
            mapped = self.map_api_data_to_standard_format(record)
            mapped['record_type'] = 'property'
            results.append(mapped)

        return results


    def search_deed(self, query: Dict[str, Any], county: str = None) -> List[Dict[str, Any]]:
        """Search deed records."""
        endpoint = "/deed/search"
        if county:
            county_config = self.COUNTY_APIS.get(county.lower().replace(' ', '_'))
            if county_config:
                endpoint = county_config.get('deed_endpoint', endpoint)

        response = self.make_request('GET', endpoint, params=query)
        data = self.validate_response(response)

        results = []
        for record in data.get('results', []):
            mapped = self.map_api_data_to_standard_format(record)
            mapped['record_type'] = 'deed'
            results.append(mapped)

        return results


    def search_lien(self, query: Dict[str, Any], county: str = None) -> List[Dict[str, Any]]:
        """Search lien records."""
        endpoint = "/lien/search"
        if county:
            county_config = self.COUNTY_APIS.get(county.lower().replace(' ', '_'))
            if county_config:
                endpoint = county_config.get('lien_endpoint', endpoint)

        response = self.make_request('GET', endpoint, params=query)
        data = self.validate_response(response)

        results = []
        for record in data.get('results', []):
            mapped = self.map_api_data_to_standard_format(record)
            mapped['record_type'] = 'lien'
            results.append(mapped)

        return results


    def get_supported_record_types(self) -> List[str]:
        """Get list of supported record types for this state."""
        return ['property', 'deed', 'lien', 'mortgage', 'tax']

    def get_state_info(self) -> Dict[str, Any]:
        """Get information about this state integration."""
        return {
            'state_code': self.STATE_CODE,
            'state_name': self.STATE_NAME,
            'counties_supported': len(COUNTY_APIS),
            'counties': self.list_counties(),
            'record_types': self.get_supported_record_types(),
            'api_class': self.__class__.__name__,
            'metrics': self.get_metrics()
        }


# Convenience function for getting a configured instance
def get_vt_api(jurisdiction_id: int, config: Dict[str, Any] = None) -> VermontAPI:
    """
    Get a configured Vermont API instance.

    Args:
        jurisdiction_id: Database jurisdiction ID
        config: Optional configuration overrides

    Returns:
        Configured VermontAPI instance
    """
    return VermontAPI(jurisdiction_id, config)
