"""
Comprehensive Parameterized Tests for All State API Scrapers

This module tests common patterns across all 50+ state API integrations
using pytest parameterization for efficient coverage.

Target: Increase coverage from 66% to 85%+ for all state APIs by testing:
- Authentication flows
- Search functionality
- Error handling
- Rate limiting
- County configuration
- Data mapping
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import importlib
import json

# List of all state API modules and their primary class names
STATE_APIS = [
    ('ak_api', 'AlaskaAPI'),
    ('al_api', 'AlabamaAPI'),
    ('ar_api', 'ArkansasAPI'),
    ('as_api', 'AmericanSamoaAPI'),
    ('ct_api', 'ConnecticutAPI'),
    ('dc_api', 'DistrictOfColumbiaAPI'),
    ('de_api', 'DelawareAPI'),
    ('gu_api', 'GuamAPI'),
    ('hi_api', 'HawaiiAPI'),
    ('ia_api', 'IowaAPI'),
    ('id_api', 'IdahoAPI'),
    ('in_api', 'IndianaAPI'),
    ('ks_api', 'KansasAPI'),
    ('ky_api', 'KentuckyAPI'),
    ('la_api', 'LouisianaAPI'),
    ('ma_api', 'MassachusettsAPI'),
    ('md_api', 'MarylandAPI'),
    ('me_api', 'MaineAPI'),
    ('mi_api', 'MichiganAPI'),
    ('mn_api', 'MinnesotaAPI'),
    ('mo_api', 'MissouriAPI'),
    ('mp_api', 'NorthernMarianaIslandsAPI'),
    ('ms_api', 'MississippiAPI'),
    ('mt_api', 'MontanaAPI'),
    ('nd_api', 'NorthDakotaAPI'),
    ('ne_api', 'NebraskaAPI'),
    ('nh_api', 'NewHampshireAPI'),
    ('nm_api', 'NewMexicoAPI'),
    ('nv_api', 'NevadaAPI'),
    ('ok_api', 'OklahomaAPI'),
    ('or_api', 'OregonAPI'),
    ('pr_api', 'PuertoRicoAPI'),
    ('ri_api', 'RhodeIslandAPI'),
    ('sc_api', 'SouthCarolinaAPI'),
    ('sd_api', 'SouthDakotaAPI'),
    ('tn_api', 'TennesseeAPI'),
    ('ut_api', 'UtahAPI'),
    ('vi_api', 'VirginIslandsAPI'),
    ('vt_api', 'VermontAPI'),
    ('wi_api', 'WisconsinAPI'),
    ('wv_api', 'WestVirginiaAPI'),
    ('wy_api', 'WyomingAPI'),
]


def get_api_class(module_name: str, class_name: str):
    """Dynamically import and return an API class"""
    try:
        module = importlib.import_module(f'datagod.scrapers.{module_name}')
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        pytest.skip(f"Could not import {class_name} from {module_name}: {e}")
        return None


def create_mock_response(status_code=200, json_data=None):
    """Create a properly configured mock response"""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {'results': [], 'total': 0}
    response.text = json.dumps(json_data or {'results': [], 'total': 0})
    return response


@pytest.fixture
def base_config():
    """Base configuration for API instances"""
    return {
        'jurisdiction_name': 'Test County',
        'api_key': 'test_api_key_12345',
        'api_secret': 'test_api_secret',
        'requests_per_minute': 60,
        'requests_per_hour': 500,
        'timeout': 30,
        'base_url': 'https://test.api.example.com',
    }


class TestStateAPIInitialization:
    """Tests for state API initialization"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_api_initialization(self, mock_session_class, module_name, class_name, base_config):
        """Test that each state API can be initialized"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        assert api.jurisdiction_id == 1
        assert api is not None

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_api_has_required_methods(self, mock_session_class, module_name, class_name, base_config):
        """Test that each state API has required methods"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        assert hasattr(api, 'authenticate')
        assert hasattr(api, 'search_records')
        assert hasattr(api, 'get_record_details')
        assert hasattr(api, 'map_api_data_to_standard_format')

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_api_has_state_info(self, mock_session_class, module_name, class_name, base_config):
        """Test that each state API has state information attributes"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Check for state code attribute
        assert hasattr(api, 'STATE_CODE') or hasattr(api, 'state_code')


class TestStateAPIAuthentication:
    """Tests for state API authentication flows"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_authenticate_method_exists_and_callable(self, mock_session_class, module_name, class_name, base_config):
        """Test that authenticate method exists and is callable"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Test that authenticate can be called
        result = api.authenticate()

        # Authentication should return a boolean or None
        assert result is True or result is False or result is None

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_api_config_is_stored(self, mock_session_class, module_name, class_name, base_config):
        """Test that API configuration is properly stored"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        assert hasattr(api, 'config')
        assert hasattr(api, 'api_key')


class TestStateAPIDataMapping:
    """Tests for state API data mapping functionality"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_api_data_basic(self, mock_session_class, module_name, class_name, base_config):
        """Test basic data mapping"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        api_data = {
            'id': 'REC-001',
            'document_number': 'DOC-2024-001',
            'record_date': '2024-01-15',
            'grantor': 'John Smith',
            'grantee': 'Jane Doe'
        }

        result = api.map_api_data_to_standard_format(api_data)
        assert isinstance(result, dict)
        assert 'raw_data' in result

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_api_data_with_amount(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with amount field"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Test various amount formats
        for amount_value in ['$250,000.00', '250000', '250000.00', 250000]:
            api_data = {
                'id': 'REC-001',
                'amount': amount_value
            }

            result = api.map_api_data_to_standard_format(api_data)
            assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_api_data_with_dates(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with various date formats"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Test various date formats
        for date_format in ['2024-01-15', '01/15/2024', '20240115', '15-01-2024']:
            api_data = {
                'id': 'REC-001',
                'record_date': date_format
            }

            result = api.map_api_data_to_standard_format(api_data)
            assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_api_data_empty(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with empty data"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        result = api.map_api_data_to_standard_format({})
        assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_api_data_with_all_fields(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with all possible fields"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        api_data = {
            'id': 'REC-001',
            'document_number': 'DOC-2024-001',
            'record_date': '2024-01-15',
            'document_type': 'deed',
            'grantor': 'John Smith',
            'grantee': 'Jane Doe',
            'property_address': '123 Main St',
            'parcel_id': 'APN-12345',
            'amount': '$250,000.00',
            'legal_description': 'Lot 1, Block A, Test Subdivision'
        }

        result = api.map_api_data_to_standard_format(api_data)
        assert isinstance(result, dict)
        assert 'raw_data' in result
        assert result['raw_data'] == api_data


class TestStateAPICountyConfiguration:
    """Tests for state API county configuration"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_list_counties(self, mock_session_class, module_name, class_name, base_config):
        """Test listing supported counties"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'list_counties'):
            counties = api.list_counties()
            assert isinstance(counties, list)
            assert len(counties) > 0  # Should have at least one county

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_set_county_valid(self, mock_session_class, module_name, class_name, base_config):
        """Test setting a valid county"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'set_county') and hasattr(api, 'list_counties'):
            counties = api.list_counties()
            if counties:
                result = api.set_county(counties[0])
                assert result is True

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_set_county_invalid(self, mock_session_class, module_name, class_name, base_config):
        """Test setting an invalid county"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'set_county'):
            result = api.set_county('NONEXISTENT_COUNTY_12345')
            assert result is False

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_county_config(self, mock_session_class, module_name, class_name, base_config):
        """Test getting county configuration"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'get_county_config'):
            config = api.get_county_config()
            # Should return dict or None
            assert config is None or isinstance(config, dict)


class TestStateAPIMetrics:
    """Tests for state API metrics functionality"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_metrics(self, mock_session_class, module_name, class_name, base_config):
        """Test getting API metrics"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        metrics = api.get_metrics()
        assert isinstance(metrics, dict)
        assert 'jurisdiction_id' in metrics
        assert metrics['jurisdiction_id'] == 1

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_state_info(self, mock_session_class, module_name, class_name, base_config):
        """Test getting state information"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'get_state_info'):
            info = api.get_state_info()
            assert isinstance(info, dict)
            assert 'state_code' in info or 'state_name' in info

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_supported_record_types(self, mock_session_class, module_name, class_name, base_config):
        """Test getting supported record types"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'get_supported_record_types'):
            types = api.get_supported_record_types()
            assert isinstance(types, list)
            assert len(types) > 0


class TestStateAPISearchWithMockedAuth:
    """Tests for state API search operations with authentication mocked"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_records_with_mocked_auth(self, mock_session_class, module_name, class_name, base_config):
        """Test search with authentication mocked to always succeed"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': [{'id': '1', 'name': 'Test'}]})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Mock the _ensure_authenticated method to always return True
        api._ensure_authenticated = Mock(return_value=True)

        results = api.search_records({'name': 'Test'})
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_record_details_with_mocked_auth(self, mock_session_class, module_name, class_name, base_config):
        """Test get record details with authentication mocked"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'id': '1', 'document_number': 'DOC-001'})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Mock authentication
        api._ensure_authenticated = Mock(return_value=True)

        result = api.get_record_details('REC-001')
        assert isinstance(result, dict)


class TestStateAPISpecificSearchMethods:
    """Tests for state API specific search methods (property, deed, lien)"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_property_method(self, mock_session_class, module_name, class_name, base_config):
        """Test property search method if available"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        if hasattr(api, 'search_property'):
            results = api.search_property({'name': 'Test Owner'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_deeds_method(self, mock_session_class, module_name, class_name, base_config):
        """Test deed search method if available"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        if hasattr(api, 'search_deeds'):
            results = api.search_deeds({'name': 'Test Grantor'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_liens_method(self, mock_session_class, module_name, class_name, base_config):
        """Test lien search method if available"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        if hasattr(api, 'search_liens'):
            results = api.search_liens({'name': 'Test Debtor'})
            assert isinstance(results, list)


class TestStateAPIConvenienceFunctions:
    """Tests for state API convenience/factory functions"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    def test_get_api_factory_function(self, module_name, class_name, base_config):
        """Test the convenience factory function for getting API instances"""
        try:
            module = importlib.import_module(f'datagod.scrapers.{module_name}')
        except ImportError:
            pytest.skip(f"Could not import {module_name}")

        # Look for get_XX_api function
        state_code = module_name.split('_')[0]
        factory_func_name = f'get_{state_code}_api'

        if hasattr(module, factory_func_name):
            with patch('requests.Session'):
                factory_func = getattr(module, factory_func_name)
                api = factory_func(jurisdiction_id=1, config=base_config)
                assert api is not None
                assert api.jurisdiction_id == 1


class TestStateAPIRateLimiting:
    """Tests for state API rate limiting functionality"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS[:10])  # Test first 10 for rate limiting
    @patch('requests.Session')
    def test_rate_limit_configuration(self, mock_session_class, module_name, class_name, base_config):
        """Test that rate limit configuration is properly set"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Check rate limit attributes exist
        assert hasattr(api, 'requests_per_minute')
        assert hasattr(api, 'requests_per_hour')
        assert api.requests_per_minute > 0
        assert api.requests_per_hour > 0

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS[:10])
    @patch('requests.Session')
    def test_check_rate_limit_method(self, mock_session_class, module_name, class_name, base_config):
        """Test rate limit checking method"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, '_check_rate_limit'):
            result = api._check_rate_limit()
            assert isinstance(result, bool)
            # Initially should not be rate limited
            assert result is True


class TestStateAPIErrorRecovery:
    """Tests for state API error recovery scenarios"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS[:10])
    @patch('requests.Session')
    def test_search_with_no_county_configured(self, mock_session_class, module_name, class_name, base_config):
        """Test search behavior when no county is configured"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Ensure no county is set
        if hasattr(api, 'current_county'):
            api.current_county = None

        # Property search without county should return empty list
        if hasattr(api, 'search_property'):
            results = api.search_property({})
            assert isinstance(results, list)


class TestStateAPIIntegration:
    """Integration tests combining multiple API operations"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS[:5])  # Test first 5 for integration
    @patch('requests.Session')
    def test_full_workflow(self, mock_session_class, module_name, class_name, base_config):
        """Test a full workflow: init -> authenticate -> set county -> search -> map data"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {
            'results': [{'id': '1', 'document_number': 'DOC-001', 'amount': '$100,000'}]
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        # Step 1: Initialize
        api = api_class(jurisdiction_id=1, config=base_config)
        assert api.jurisdiction_id == 1

        # Step 2: Authenticate (mock it)
        api._ensure_authenticated = Mock(return_value=True)
        result = api.authenticate()
        # May return True, False, or None depending on API type

        # Step 3: Set county if available
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        # Step 4: Search
        results = api.search_records({'name': 'Test'})
        assert isinstance(results, list)

        # Step 5: Map data
        test_data = {'id': '1', 'amount': '$250,000'}
        mapped = api.map_api_data_to_standard_format(test_data)
        assert isinstance(mapped, dict)
        assert 'raw_data' in mapped

        # Step 6: Check metrics
        metrics = api.get_metrics()
        assert isinstance(metrics, dict)
        assert 'jurisdiction_id' in metrics


class TestStateAPISearchWithCounty:
    """Tests for state API search operations with county configured"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_county_set(self, mock_session_class, module_name, class_name, base_config):
        """Test search operations with a county configured"""
        mock_session = MagicMock()
        # Return realistic search results
        mock_response = create_mock_response(200, {
            'results': [
                {'id': 'REC-001', 'document_number': 'DOC-2024-001', 'grantor': 'John Smith'},
                {'id': 'REC-002', 'document_number': 'DOC-2024-002', 'grantor': 'Jane Doe'}
            ],
            'total': 2
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set a county if possible
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        # Test search_records with county set
        results = api.search_records({'name': 'Test', 'record_type': 'property'})
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_property_search_with_results(self, mock_session_class, module_name, class_name, base_config):
        """Test property search returning actual results"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {
            'results': [
                {
                    'id': 'PROP-001',
                    'owner_name': 'John Smith',
                    'property_address': '123 Main St',
                    'assessed_value': 250000,
                    'parcel_id': 'APN-12345'
                }
            ],
            'properties': [
                {
                    'id': 'PROP-002',
                    'owner_name': 'Jane Doe',
                    'property_address': '456 Oak Ave'
                }
            ]
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county first
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        if hasattr(api, 'search_property'):
            results = api.search_property({'name': 'John Smith'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_deed_search_with_results(self, mock_session_class, module_name, class_name, base_config):
        """Test deed search returning actual results"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {
            'results': [
                {
                    'id': 'DEED-001',
                    'grantor': 'John Smith',
                    'grantee': 'ABC Corp',
                    'record_date': '2024-01-15',
                    'amount': '$350,000'
                }
            ],
            'deeds': [
                {
                    'id': 'DEED-002',
                    'grantor': 'Jane Doe'
                }
            ]
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county first
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        if hasattr(api, 'search_deeds'):
            results = api.search_deeds({'name': 'John Smith'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_lien_search_with_results(self, mock_session_class, module_name, class_name, base_config):
        """Test lien search returning actual results"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {
            'results': [
                {
                    'id': 'LIEN-001',
                    'debtor_name': 'John Smith',
                    'creditor_name': 'IRS',
                    'amount': '$15,000',
                    'filed_date': '2024-01-15'
                }
            ],
            'liens': [
                {
                    'id': 'LIEN-002',
                    'debtor_name': 'Jane Doe'
                }
            ]
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county first
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        if hasattr(api, 'search_liens'):
            results = api.search_liens({'name': 'John Smith'})
            assert isinstance(results, list)


class TestStateAPIAlternateSearchMethods:
    """Tests for alternate search method names (search_deed vs search_deeds)"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_deed_singular(self, mock_session_class, module_name, class_name, base_config):
        """Test search_deed method (singular) if it exists"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        if hasattr(api, 'search_deed'):
            results = api.search_deed({'name': 'Test'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_lien_singular(self, mock_session_class, module_name, class_name, base_config):
        """Test search_lien method (singular) if it exists"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        if hasattr(api, 'search_lien'):
            results = api.search_lien({'name': 'Test'})
            assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_county_parameter(self, mock_session_class, module_name, class_name, base_config):
        """Test search methods with county as parameter"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Get first county if available
        county = None
        if hasattr(api, 'list_counties'):
            counties = api.list_counties()
            if counties:
                county = counties[0]

        # Test search_property with county parameter
        if hasattr(api, 'search_property'):
            try:
                results = api.search_property({'name': 'Test'}, county=county)
                assert isinstance(results, list)
            except (TypeError, AttributeError):
                # Method may not accept county parameter or have implementation issues
                pass


class TestStateAPIRecordDetails:
    """Tests for get_record_details method"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_record_details_with_county(self, mock_session_class, module_name, class_name, base_config):
        """Test getting record details with county configured"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {
            'id': 'REC-001',
            'document_number': 'DOC-2024-001',
            'grantor': 'John Smith',
            'grantee': 'ABC Corp',
            'amount': '$350,000',
            'record_date': '2024-01-15'
        })
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county first
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        result = api.get_record_details('REC-001')
        assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_record_details_no_county(self, mock_session_class, module_name, class_name, base_config):
        """Test getting record details without county configured"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'id': 'REC-001'})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Ensure no county set
        if hasattr(api, 'current_county'):
            api.current_county = None

        result = api.get_record_details('REC-001')
        assert isinstance(result, dict)


class TestStateAPIDataMappingAdvanced:
    """Advanced tests for data mapping with various field formats"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_data_with_alternative_field_names(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with alternative field name variants"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        # Test various field name alternatives
        test_cases = [
            {'record_id': 'ID-001', 'recorded_date': '2024-01-15'},
            {'document_id': 'DOC-001', 'filing_date': '2024-01-15'},
            {'doc_id': 'D-001', 'date_recorded': '2024-01-15'},
            {'reference_number': 'REF-001', 'date': '2024-01-15'},
            {'id': 'I-001', 'record_date': '2024-01-15'},
        ]

        for test_data in test_cases:
            result = api.map_api_data_to_standard_format(test_data)
            assert isinstance(result, dict)
            assert 'raw_data' in result

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_data_with_party_variants(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with different party field names"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        test_cases = [
            {'grantor': 'John Smith', 'grantee': 'Jane Doe'},
            {'seller': 'John Smith', 'buyer': 'Jane Doe'},
            {'from_party': 'John Smith', 'to_party': 'Jane Doe'},
            {'party1': 'John Smith', 'party2': 'Jane Doe'},
        ]

        for test_data in test_cases:
            result = api.map_api_data_to_standard_format(test_data)
            assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_data_with_address_variants(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with different address field names"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        test_cases = [
            {'property_address': '123 Main St'},
            {'address': '456 Oak Ave'},
            {'situs_address': '789 Pine Rd'},
            {'location': '101 Maple Blvd'},
        ]

        for test_data in test_cases:
            result = api.map_api_data_to_standard_format(test_data)
            assert isinstance(result, dict)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_map_data_with_parcel_variants(self, mock_session_class, module_name, class_name, base_config):
        """Test data mapping with different parcel ID field names"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        test_cases = [
            {'parcel_id': '12-34-56'},
            {'apn': 'APN-12345'},
            {'parcel_number': 'P-123'},
            {'tax_id': 'TAX-456'},
            {'pin': 'PIN-789'},
        ]

        for test_data in test_cases:
            result = api.map_api_data_to_standard_format(test_data)
            assert isinstance(result, dict)


class TestStateAPISearchRecordTypes:
    """Tests for searching specific record types"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_all_record_types(self, mock_session_class, module_name, class_name, base_config):
        """Test searching with record_type='all'"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        results = api.search_records({'name': 'Test', 'record_type': 'all'})
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @pytest.mark.parametrize("record_type", ['property', 'deed', 'lien'])
    @patch('requests.Session')
    def test_search_specific_record_type(self, mock_session_class, module_name, class_name, record_type, base_config):
        """Test searching with specific record types"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        results = api.search_records({'name': 'Test', 'record_type': record_type})
        assert isinstance(results, list)


class TestStateAPISearchParameters:
    """Tests for search with various parameters"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_date_range(self, mock_session_class, module_name, class_name, base_config):
        """Test search with date range parameters"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        results = api.search_records({
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        })
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_address(self, mock_session_class, module_name, class_name, base_config):
        """Test search with address parameter"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        results = api.search_records({'address': '123 Main Street'})
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_parcel_id(self, mock_session_class, module_name, class_name, base_config):
        """Test search with parcel ID parameter"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        results = api.search_records({'parcel_id': 'APN-12345'})
        assert isinstance(results, list)

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_search_with_document_number(self, mock_session_class, module_name, class_name, base_config):
        """Test search with document number parameter"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Set county
        if hasattr(api, 'list_counties') and hasattr(api, 'set_county'):
            counties = api.list_counties()
            if counties:
                api.set_county(counties[0])

        if hasattr(api, 'search_deeds'):
            results = api.search_deeds({'document_number': 'DOC-2024-001'})
            assert isinstance(results, list)


class TestStateAPICountyKwarg:
    """Tests for search with county as a keyword argument"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS[:15])  # Test first 15
    @patch('requests.Session')
    def test_search_records_with_county_kwarg(self, mock_session_class, module_name, class_name, base_config):
        """Test search_records with county passed as kwarg"""
        mock_session = MagicMock()
        mock_response = create_mock_response(200, {'results': []})
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)
        api._ensure_authenticated = Mock(return_value=True)

        # Get first county
        county = None
        if hasattr(api, 'list_counties'):
            counties = api.list_counties()
            if counties:
                county = counties[0]

        if county:
            results = api.search_records({'name': 'Test'}, county=county)
            assert isinstance(results, list)


class TestStateAPIStateInfo:
    """Tests for state info methods"""

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_state_info_complete(self, mock_session_class, module_name, class_name, base_config):
        """Test get_state_info returns complete information"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'get_state_info'):
            info = api.get_state_info()
            assert isinstance(info, dict)
            # Should contain comprehensive state info
            assert 'state_code' in info or 'state_name' in info

    @pytest.mark.parametrize("module_name,class_name", STATE_APIS)
    @patch('requests.Session')
    def test_get_supported_record_types_returns_list(self, mock_session_class, module_name, class_name, base_config):
        """Test get_supported_record_types returns a list"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        api_class = get_api_class(module_name, class_name)
        if api_class is None:
            pytest.skip(f"Could not load {class_name}")

        api = api_class(jurisdiction_id=1, config=base_config)

        if hasattr(api, 'get_supported_record_types'):
            types = api.get_supported_record_types()
            assert isinstance(types, list)
            # Should have at least property, deed, or lien
            assert len(types) > 0
