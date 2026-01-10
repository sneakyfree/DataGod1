"""
Tests for the new state scrapers: Washington, Colorado, North Carolina, Virginia, New Jersey.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestWashingtonCountyAPI:
    """Tests for Washington state scrapers."""

    def test_initialization(self):
        """Test WashingtonCountyAPI initialization."""
        from datagod.scrapers.washington_api import WashingtonCountyAPI

        config = {
            'jurisdiction_name': 'King County',
            'requests_per_minute': 30
        }
        api = WashingtonCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == 'king'
        assert 'property_search' in api.available_features
        assert api.base_url != ''

    def test_king_county_specialization(self):
        """Test KingCountyAPI specialization."""
        from datagod.scrapers.washington_api import KingCountyAPI

        api = KingCountyAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'king'
        assert 'mortgage_records' in api.available_features

    def test_property_mapping(self):
        """Test property data mapping to standard format."""
        from datagod.scrapers.washington_api import WashingtonCountyAPI

        api = WashingtonCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'King County'})

        raw_data = {
            'parcel_number': '1234567890',
            'owner_name': 'John Doe',
            'site_address': '123 Main St',
            'city': 'Seattle',
            'assessed_value': 500000,
            'legal_description': 'Lot 1 Block 2'
        }

        result = api._map_property_to_standard(raw_data)

        assert result['record_type'] == 'property'
        assert result['record_id'] == '1234567890'
        assert result['grantee'] == 'John Doe'
        assert result['state'] == 'WA'
        assert result['amount'] == 500000


class TestColoradoCountyAPI:
    """Tests for Colorado state scrapers."""

    def test_initialization(self):
        """Test ColoradoCountyAPI initialization."""
        from datagod.scrapers.colorado_api import ColoradoCountyAPI

        config = {
            'jurisdiction_name': 'Denver County',
            'requests_per_minute': 30
        }
        api = ColoradoCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == 'denver'
        assert 'property_search' in api.available_features

    def test_denver_county_specialization(self):
        """Test DenverCountyAPI specialization."""
        from datagod.scrapers.colorado_api import DenverCountyAPI

        api = DenverCountyAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'denver'
        assert 'mortgage_records' in api.available_features

    def test_property_mapping(self):
        """Test property data mapping to standard format."""
        from datagod.scrapers.colorado_api import ColoradoCountyAPI

        api = ColoradoCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Denver County'})

        raw_data = {
            'schedule_number': 'R0123456',
            'owner_name': 'Jane Smith',
            'situs_address': '456 Broadway',
            'city': 'Denver',
            'actual_value': 750000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result['record_type'] == 'property'
        assert result['record_id'] == 'R0123456'
        assert result['state'] == 'CO'
        assert result['amount'] == 750000


class TestNorthCarolinaCountyAPI:
    """Tests for North Carolina state scrapers."""

    def test_initialization(self):
        """Test NorthCarolinaCountyAPI initialization."""
        from datagod.scrapers.northcarolina_api import NorthCarolinaCountyAPI

        config = {
            'jurisdiction_name': 'Wake County',
            'requests_per_minute': 30
        }
        api = NorthCarolinaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == 'wake'
        assert 'property_search' in api.available_features

    def test_mecklenburg_county_specialization(self):
        """Test MecklenburgCountyAPI specialization."""
        from datagod.scrapers.northcarolina_api import MecklenburgCountyAPI

        api = MecklenburgCountyAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'mecklenburg'
        assert 'mortgage_records' in api.available_features

    def test_property_mapping(self):
        """Test property data mapping to standard format."""
        from datagod.scrapers.northcarolina_api import NorthCarolinaCountyAPI

        api = NorthCarolinaCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Wake County'})

        raw_data = {
            'pin': '0123456789',
            'owner_name': 'Bob Johnson',
            'property_address': '789 Oak Ave',
            'city': 'Raleigh',
            'total_value': 425000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result['record_type'] == 'property'
        assert result['record_id'] == '0123456789'
        assert result['state'] == 'NC'
        assert result['city'] == 'Raleigh'


class TestVirginiaCountyAPI:
    """Tests for Virginia state scrapers."""

    def test_initialization(self):
        """Test VirginiaCountyAPI initialization."""
        from datagod.scrapers.virginia_api import VirginiaCountyAPI

        config = {
            'jurisdiction_name': 'Fairfax County',
            'requests_per_minute': 30
        }
        api = VirginiaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == 'fairfax'
        assert 'property_search' in api.available_features

    def test_fairfax_county_specialization(self):
        """Test FairfaxCountyAPI specialization."""
        from datagod.scrapers.virginia_api import FairfaxCountyAPI

        api = FairfaxCountyAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'fairfax'
        assert 'mortgage_records' in api.available_features

    def test_virginia_beach_city(self):
        """Test VirginiaBeachCityAPI for independent city."""
        from datagod.scrapers.virginia_api import VirginiaBeachCityAPI

        api = VirginiaBeachCityAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'virginia-beach'

    def test_property_mapping(self):
        """Test property data mapping to standard format."""
        from datagod.scrapers.virginia_api import VirginiaCountyAPI

        api = VirginiaCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Fairfax County'})

        raw_data = {
            'tax_map_number': '0123-45-6789',
            'owner_name': 'Alice Brown',
            'property_address': '321 Elm St',
            'city': 'Fairfax',
            'total_value': 850000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result['record_type'] == 'property'
        assert result['record_id'] == '0123-45-6789'
        assert result['state'] == 'VA'


class TestNewJerseyCountyAPI:
    """Tests for New Jersey state scrapers."""

    def test_initialization(self):
        """Test NewJerseyCountyAPI initialization."""
        from datagod.scrapers.newjersey_api import NewJerseyCountyAPI

        config = {
            'jurisdiction_name': 'Bergen County',
            'requests_per_minute': 30
        }
        api = NewJerseyCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == 'bergen'
        assert 'property_search' in api.available_features

    def test_bergen_county_specialization(self):
        """Test BergenCountyAPI specialization."""
        from datagod.scrapers.newjersey_api import BergenCountyAPI

        api = BergenCountyAPI(jurisdiction_id=1, config={})
        assert api.county_name == 'bergen'
        assert 'mortgage_records' in api.available_features

    def test_block_lot_mapping(self):
        """Test NJ block/lot property ID mapping."""
        from datagod.scrapers.newjersey_api import NewJerseyCountyAPI

        api = NewJerseyCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Bergen County'})

        raw_data = {
            'block': '123',
            'lot': '45',
            'qualifier': 'C001',
            'owner_name': 'Charlie Davis',
            'property_location': '555 Park Blvd',
            'municipality': 'Hackensack',
            'total_assessment': 625000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result['record_type'] == 'property'
        assert result['record_id'] == '123/45/C001'
        assert result['state'] == 'NJ'
        assert result['city'] == 'Hackensack'


class TestScraperRegistry:
    """Tests for scraper registry functionality."""

    def test_get_scraper_for_new_states(self):
        """Test getting scrapers for new states."""
        from datagod.scrapers import get_scraper_for_jurisdiction

        # Washington
        wa_scraper = get_scraper_for_jurisdiction('WA')
        assert wa_scraper.__name__ == 'WashingtonCountyAPI'

        wa_king = get_scraper_for_jurisdiction('WA', 'king')
        assert wa_king.__name__ == 'KingCountyAPI'

        # Colorado
        co_scraper = get_scraper_for_jurisdiction('CO')
        assert co_scraper.__name__ == 'ColoradoCountyAPI'

        # North Carolina
        nc_scraper = get_scraper_for_jurisdiction('NC')
        assert nc_scraper.__name__ == 'NorthCarolinaCountyAPI'

        # Virginia
        va_scraper = get_scraper_for_jurisdiction('VA')
        assert va_scraper.__name__ == 'VirginiaCountyAPI'

        # New Jersey
        nj_scraper = get_scraper_for_jurisdiction('NJ')
        assert nj_scraper.__name__ == 'NewJerseyCountyAPI'

    def test_list_supported_states_includes_new_states(self):
        """Test that new states are in supported list."""
        from datagod.scrapers import list_supported_states

        states = list_supported_states()

        assert 'WA' in states
        assert 'CO' in states
        assert 'NC' in states
        assert 'VA' in states
        assert 'NJ' in states

    def test_total_supported_counties(self):
        """Test total county count includes new states."""
        from datagod.scrapers import TOTAL_SUPPORTED_COUNTIES, SUPPORTED_COUNTIES

        # New states add 44 counties (8+8+10+8+10)
        assert SUPPORTED_COUNTIES['WA'] == 8
        assert SUPPORTED_COUNTIES['CO'] == 8
        assert SUPPORTED_COUNTIES['NC'] == 10
        assert SUPPORTED_COUNTIES['VA'] == 8
        assert SUPPORTED_COUNTIES['NJ'] == 10

        # Total should be 137 (93 original + 44 new)
        assert TOTAL_SUPPORTED_COUNTIES == 137


class TestDeedMapping:
    """Tests for deed record mapping across all new states."""

    def test_washington_deed_mapping(self):
        """Test Washington deed record mapping."""
        from datagod.scrapers.washington_api import WashingtonCountyAPI

        api = WashingtonCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'King County'})

        raw_data = {
            'document_number': 'DOC-2024-001234',
            'document_type': 'WARRANTY DEED',
            'grantor': 'Seller LLC',
            'grantee': 'Buyer Inc',
            'excise_tax_paid': 640,  # $640 = ~$50,000 sale
            'recording_date': '2024-01-15'
        }

        result = api._map_deed_to_standard(raw_data)

        assert result['record_type'] == 'warranty deed'
        assert result['record_id'] == 'DOC-2024-001234'
        assert result['grantor'] == 'Seller LLC'
        assert result['grantee'] == 'Buyer Inc'
        assert result['state'] == 'WA'

    def test_colorado_deed_mapping(self):
        """Test Colorado deed record mapping."""
        from datagod.scrapers.colorado_api import ColoradoCountyAPI

        api = ColoradoCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Denver County'})

        raw_data = {
            'reception_number': '2024001234',
            'document_type': 'DEED OF TRUST',
            'grantor': 'Borrower Name',
            'grantee': 'Lender Bank',
            'consideration': 450000,
            'recording_date': '2024-02-20'
        }

        result = api._map_deed_to_standard(raw_data)

        assert result['record_type'] == 'deed of trust'
        assert result['document_number'] == '2024001234'
        assert result['amount'] == 450000
        assert result['state'] == 'CO'

    def test_northcarolina_deed_mapping(self):
        """Test North Carolina deed record mapping."""
        from datagod.scrapers.northcarolina_api import NorthCarolinaCountyAPI

        api = NorthCarolinaCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Wake County'})

        raw_data = {
            'instrument_number': '2024-00012345',
            'document_type': 'QUIT CLAIM DEED',
            'grantor': 'Previous Owner',
            'grantee': 'New Owner',
            'excise_tax': 500,  # $500 = $250,000 sale
            'book': '12345',
            'page': '678'
        }

        result = api._map_deed_to_standard(raw_data)

        assert result['record_type'] == 'quit claim deed'
        assert result['book_page'] == '12345/678'
        assert result['state'] == 'NC'

    def test_virginia_deed_mapping(self):
        """Test Virginia deed record mapping."""
        from datagod.scrapers.virginia_api import VirginiaCountyAPI

        api = VirginiaCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Fairfax County'})

        raw_data = {
            'instrument_number': 'INST-2024-001234',
            'instrument_type': 'SPECIAL WARRANTY DEED',
            'grantor': 'Estate of Smith',
            'grantee': 'New Family Trust',
            'consideration': 1200000,
            'instrument_date': '2024-03-10'
        }

        result = api._map_deed_to_standard(raw_data)

        assert result['record_type'] == 'special warranty deed'
        assert result['amount'] == 1200000
        assert result['state'] == 'VA'

    def test_newjersey_deed_mapping(self):
        """Test New Jersey deed record mapping."""
        from datagod.scrapers.newjersey_api import NewJerseyCountyAPI

        api = NewJerseyCountyAPI(jurisdiction_id=1, config={'jurisdiction_name': 'Bergen County'})

        raw_data = {
            'document_number': 'NJ-2024-001234',
            'document_type': 'BARGAIN AND SALE DEED',
            'grantor': 'Corporate Seller',
            'grantee': 'Individual Buyer',
            'municipality': 'Fort Lee',
            'consideration': 875000,
            'book': '5678',
            'page': '123'
        }

        result = api._map_deed_to_standard(raw_data)

        assert result['record_type'] == 'bargain and sale deed'
        assert result['city'] == 'Fort Lee'
        assert result['book_page'] == '5678/123'
        assert result['state'] == 'NJ'
