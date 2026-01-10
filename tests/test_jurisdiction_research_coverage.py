#!/usr/bin/env python3
"""
Comprehensive tests for datagod/scrapers/jurisdiction_research.py
Tests Jurisdiction dataclass and JurisdictionResearcher class for full coverage
"""

import pytest
import os
import json
import csv
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime

# Import the actual module
from datagod.scrapers.jurisdiction_research import (
    Jurisdiction,
    JurisdictionResearcher,
    main,
    logger
)


class TestJurisdictionDataclass:
    """Tests for the Jurisdiction dataclass"""

    def test_jurisdiction_creation_minimal(self):
        """Test creating Jurisdiction with minimal required fields"""
        j = Jurisdiction(name="Test County, CA", state="CA")

        assert j.name == "Test County, CA"
        assert j.state == "CA"
        assert j.county is None
        assert j.type == 'county'
        assert j.website is None
        assert j.api_available == False
        assert j.api_documentation is None
        assert j.scraper_needed == True
        assert j.data_volume == 'unknown'
        assert j.priority == 3
        assert j.notes is None

    def test_jurisdiction_creation_full(self):
        """Test creating Jurisdiction with all fields"""
        j = Jurisdiction(
            name="Los Angeles County, CA",
            state="CA",
            county="Los Angeles",
            type="county",
            website="https://www.lacounty.gov",
            api_available=True,
            api_documentation="https://api.lacounty.gov/docs",
            scraper_needed=False,
            data_volume="high",
            priority=1,
            notes="Major metropolitan area"
        )

        assert j.name == "Los Angeles County, CA"
        assert j.state == "CA"
        assert j.county == "Los Angeles"
        assert j.type == "county"
        assert j.website == "https://www.lacounty.gov"
        assert j.api_available == True
        assert j.api_documentation == "https://api.lacounty.gov/docs"
        assert j.scraper_needed == False
        assert j.data_volume == "high"
        assert j.priority == 1
        assert j.notes == "Major metropolitan area"

    def test_jurisdiction_type_city(self):
        """Test Jurisdiction with type='city'"""
        j = Jurisdiction(name="New York City", state="NY", type="city")
        assert j.type == "city"

    def test_jurisdiction_type_state(self):
        """Test Jurisdiction with type='state'"""
        j = Jurisdiction(name="California", state="CA", type="state")
        assert j.type == "state"

    def test_jurisdiction_different_priorities(self):
        """Test Jurisdiction with different priority levels"""
        j1 = Jurisdiction(name="High Priority", state="CA", priority=1)
        j2 = Jurisdiction(name="Medium Priority", state="TX", priority=2)
        j3 = Jurisdiction(name="Low Priority", state="FL", priority=3)

        assert j1.priority == 1
        assert j2.priority == 2
        assert j3.priority == 3

    def test_jurisdiction_data_volumes(self):
        """Test Jurisdiction with different data volume levels"""
        j1 = Jurisdiction(name="High Volume", state="CA", data_volume="high")
        j2 = Jurisdiction(name="Medium Volume", state="TX", data_volume="medium")
        j3 = Jurisdiction(name="Low Volume", state="FL", data_volume="low")
        j4 = Jurisdiction(name="Unknown Volume", state="NY")

        assert j1.data_volume == "high"
        assert j2.data_volume == "medium"
        assert j3.data_volume == "low"
        assert j4.data_volume == "unknown"


class TestJurisdictionResearcherInit:
    """Tests for JurisdictionResearcher initialization"""

    def test_researcher_init_creates_directory(self):
        """Test that init creates the base directory"""
        with patch('os.makedirs') as mock_makedirs:
            researcher = JurisdictionResearcher()
            mock_makedirs.assert_called_once_with('datagod/scrapers/data', exist_ok=True)

    def test_researcher_init_sets_base_dir(self):
        """Test that base_dir is set correctly"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            assert researcher.base_dir == 'datagod/scrapers/data'

    def test_researcher_init_sets_user_agent(self):
        """Test that user_agent is set correctly"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            assert 'Mozilla' in researcher.user_agent
            assert 'Chrome' in researcher.user_agent


class TestGetStateList:
    """Tests for get_state_list method"""

    def test_get_state_list_returns_list(self):
        """Test that get_state_list returns a list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            assert isinstance(states, list)

    def test_get_state_list_count(self):
        """Test that get_state_list returns all 50 states + territories"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            # 50 states + DC + PR + GU + VI + AS + MP = 56
            assert len(states) == 56

    def test_get_state_list_structure(self):
        """Test that each state has code and name"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            for state in states:
                assert 'code' in state
                assert 'name' in state
                assert len(state['code']) == 2

    def test_get_state_list_contains_california(self):
        """Test that California is in the list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            ca = next((s for s in states if s['code'] == 'CA'), None)
            assert ca is not None
            assert ca['name'] == 'California'

    def test_get_state_list_contains_texas(self):
        """Test that Texas is in the list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            tx = next((s for s in states if s['code'] == 'TX'), None)
            assert tx is not None
            assert tx['name'] == 'Texas'

    def test_get_state_list_contains_dc(self):
        """Test that DC is in the list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            dc = next((s for s in states if s['code'] == 'DC'), None)
            assert dc is not None
            assert dc['name'] == 'District of Columbia'

    def test_get_state_list_contains_territories(self):
        """Test that territories are in the list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            states = researcher.get_state_list()
            codes = [s['code'] for s in states]
            assert 'PR' in codes  # Puerto Rico
            assert 'GU' in codes  # Guam
            assert 'VI' in codes  # Virgin Islands
            assert 'AS' in codes  # American Samoa
            assert 'MP' in codes  # Northern Mariana Islands


class TestFetchStateCounties:
    """Tests for fetch_state_counties method"""

    def test_fetch_state_counties_california(self):
        """Test fetching California counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('CA')
            assert isinstance(counties, list)
            assert len(counties) == 10  # Mock data has 10 CA counties

    def test_fetch_state_counties_texas(self):
        """Test fetching Texas counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('TX')
            assert len(counties) == 10  # Mock data has 10 TX counties

    def test_fetch_state_counties_florida(self):
        """Test fetching Florida counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('FL')
            assert len(counties) == 10  # Mock data has 10 FL counties

    def test_fetch_state_counties_new_york(self):
        """Test fetching New York counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('NY')
            assert len(counties) == 10  # Mock data has 10 NY counties

    def test_fetch_state_counties_illinois(self):
        """Test fetching Illinois counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('IL')
            assert len(counties) == 10  # Mock data has 10 IL counties

    def test_fetch_state_counties_unknown_state(self):
        """Test fetching counties for unknown state returns empty list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('ZZ')
            assert counties == []

    def test_fetch_state_counties_with_request_success(self):
        """Test fetch_state_counties with successful HTTP request"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.raise_for_status = MagicMock()

            with patch('requests.get', return_value=mock_response):
                counties = researcher.fetch_state_counties('CA')
                # Falls back to mock data
                assert len(counties) == 10

    def test_fetch_state_counties_with_request_failure(self):
        """Test fetch_state_counties with HTTP request failure"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with patch('requests.get', side_effect=Exception("Network error")):
                counties = researcher.fetch_state_counties('CA')
                # Falls back to mock data on error
                assert len(counties) == 10

    def test_fetch_state_counties_structure(self):
        """Test that counties have name and fips fields"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher.fetch_state_counties('CA')
            for county in counties:
                assert 'name' in county
                assert 'fips' in county


class TestGetMockCounties:
    """Tests for _get_mock_counties private method"""

    def test_get_mock_counties_california(self):
        """Test mock counties for California"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher._get_mock_counties('CA')
            county_names = [c['name'] for c in counties]
            assert 'Los Angeles' in county_names
            assert 'San Diego' in county_names
            assert 'Orange' in county_names

    def test_get_mock_counties_texas(self):
        """Test mock counties for Texas"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher._get_mock_counties('TX')
            county_names = [c['name'] for c in counties]
            assert 'Harris' in county_names
            assert 'Dallas' in county_names
            assert 'Travis' in county_names

    def test_get_mock_counties_florida(self):
        """Test mock counties for Florida"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher._get_mock_counties('FL')
            county_names = [c['name'] for c in counties]
            assert 'Miami-Dade' in county_names
            assert 'Broward' in county_names

    def test_get_mock_counties_invalid_state(self):
        """Test mock counties for invalid state returns empty list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            counties = researcher._get_mock_counties('XX')
            assert counties == []


class TestResearchJurisdiction:
    """Tests for research_jurisdiction method"""

    def test_research_jurisdiction_basic(self):
        """Test researching a basic jurisdiction"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            j = researcher.research_jurisdiction('CA', 'Sacramento')

            assert isinstance(j, Jurisdiction)
            assert j.name == "Sacramento County, CA"
            assert j.state == "CA"
            assert j.county == "Sacramento"
            assert j.type == "county"

    def test_research_jurisdiction_website_format(self):
        """Test that website URL is formatted correctly"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            j = researcher.research_jurisdiction('CA', 'Los Angeles')

            assert j.website == "https://www.losangelescountyca.gov"

    def test_research_jurisdiction_website_spaces(self):
        """Test website URL with spaces in county name"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()
            j = researcher.research_jurisdiction('FL', 'Palm Beach')

            # Spaces should be removed from URL
            assert ' ' not in j.website

    def test_research_high_priority_california(self):
        """Test high priority California counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Los Angeles is high priority
            j = researcher.research_jurisdiction('CA', 'Los Angeles')
            assert j.priority == 1
            assert j.data_volume == 'high'
            assert 'High priority' in j.notes

    def test_research_high_priority_texas(self):
        """Test high priority Texas counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Harris (Houston) is high priority
            j = researcher.research_jurisdiction('TX', 'Harris')
            assert j.priority == 1
            assert j.data_volume == 'high'

    def test_research_high_priority_florida(self):
        """Test high priority Florida counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Miami-Dade is high priority
            j = researcher.research_jurisdiction('FL', 'Miami-Dade')
            assert j.priority == 1
            assert j.data_volume == 'high'

    def test_research_high_priority_new_york(self):
        """Test high priority New York counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Kings (Brooklyn) is high priority
            j = researcher.research_jurisdiction('NY', 'Kings')
            assert j.priority == 1

    def test_research_high_priority_illinois(self):
        """Test high priority Illinois counties"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Cook (Chicago) is high priority
            j = researcher.research_jurisdiction('IL', 'Cook')
            assert j.priority == 1

    def test_research_low_priority_county(self):
        """Test that non-major counties get lower priority"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Small county not in high priority list
            j = researcher.research_jurisdiction('CA', 'Alpine')
            assert j.priority == 2
            assert j.data_volume == 'medium'
            assert j.notes == 'Initial research needed'

    def test_research_low_priority_state(self):
        """Test that counties in non-top states get default priority"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            # Wyoming county - not in top 5 states
            j = researcher.research_jurisdiction('WY', 'Laramie')
            assert j.priority == 2  # Default priority


class TestSaveJurisdictionData:
    """Tests for save_jurisdiction_data method"""

    def test_save_jurisdiction_data_csv(self):
        """Test saving jurisdiction data to CSV"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            jurisdictions = [
                Jurisdiction(name="Test County, CA", state="CA", county="Test"),
                Jurisdiction(name="Another County, TX", state="TX", county="Another")
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.save_jurisdiction_data(jurisdictions, 'test.csv')

                csv_path = os.path.join(tmpdir, 'test.csv')
                assert os.path.exists(csv_path)

                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    assert len(rows) == 2
                    assert rows[0]['name'] == "Test County, CA"

    def test_save_jurisdiction_data_json(self):
        """Test saving jurisdiction data to JSON"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            jurisdictions = [
                Jurisdiction(name="Test County, CA", state="CA", county="Test"),
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.save_jurisdiction_data(jurisdictions, 'test.csv')

                json_path = os.path.join(tmpdir, 'test.json')
                assert os.path.exists(json_path)

                with open(json_path, 'r') as f:
                    data = json.load(f)
                    assert len(data) == 1
                    assert data[0]['name'] == "Test County, CA"

    def test_save_jurisdiction_data_all_fields(self):
        """Test that all fields are saved correctly"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            jurisdictions = [
                Jurisdiction(
                    name="Full Test County, CA",
                    state="CA",
                    county="Full Test",
                    type="county",
                    website="https://test.gov",
                    api_available=True,
                    api_documentation="https://api.test.gov/docs",
                    scraper_needed=False,
                    data_volume="high",
                    priority=1,
                    notes="Test notes"
                )
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.save_jurisdiction_data(jurisdictions, 'full_test.csv')

                json_path = os.path.join(tmpdir, 'full_test.json')
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    j = data[0]
                    assert j['name'] == "Full Test County, CA"
                    assert j['state'] == "CA"
                    assert j['county'] == "Full Test"
                    assert j['type'] == "county"
                    assert j['website'] == "https://test.gov"
                    assert j['api_available'] == True
                    assert j['api_documentation'] == "https://api.test.gov/docs"
                    assert j['scraper_needed'] == False
                    assert j['data_volume'] == "high"
                    assert j['priority'] == 1
                    assert j['notes'] == "Test notes"

    def test_save_jurisdiction_data_empty_list(self):
        """Test saving empty jurisdiction list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.save_jurisdiction_data([], 'empty.csv')

                csv_path = os.path.join(tmpdir, 'empty.csv')
                json_path = os.path.join(tmpdir, 'empty.json')

                assert os.path.exists(csv_path)
                assert os.path.exists(json_path)

                with open(json_path, 'r') as f:
                    data = json.load(f)
                    assert data == []


class TestResearchTopStates:
    """Tests for research_top_states method"""

    def test_research_top_states_default(self):
        """Test researching default top 5 states"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                jurisdictions = researcher.research_top_states()

                # 5 states * 10 counties each = 50 jurisdictions
                assert len(jurisdictions) == 50

    def test_research_top_states_custom(self):
        """Test researching custom state list"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                jurisdictions = researcher.research_top_states(['CA', 'TX'])

                # 2 states * 10 counties each = 20 jurisdictions
                assert len(jurisdictions) == 20

    def test_research_top_states_single_state(self):
        """Test researching single state"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                jurisdictions = researcher.research_top_states(['CA'])

                assert len(jurisdictions) == 10

    def test_research_top_states_saves_data(self):
        """Test that research_top_states saves data files"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.research_top_states(['CA'])

                # Check that CSV file was created
                files = os.listdir(tmpdir)
                csv_files = [f for f in files if f.endswith('.csv')]
                json_files = [f for f in files if f.endswith('.json')]

                assert len(csv_files) == 1
                assert len(json_files) == 1
                assert 'jurisdictions_top_states_' in csv_files[0]


class TestResearchAllStates:
    """Tests for research_all_states method"""

    def test_research_all_states(self):
        """Test researching all states"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                jurisdictions = researcher.research_all_states()

                # Only 5 states have mock county data, others return empty
                # CA, TX, FL, NY, IL = 5 states * 10 counties = 50 jurisdictions
                assert len(jurisdictions) == 50

    def test_research_all_states_saves_data(self):
        """Test that research_all_states saves data files"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir
                researcher.research_all_states()

                files = os.listdir(tmpdir)
                csv_files = [f for f in files if f.endswith('.csv')]

                assert len(csv_files) == 1
                assert 'jurisdictions_all_states_' in csv_files[0]


class TestMainFunction:
    """Tests for the main() function"""

    def test_main_choice_1(self):
        """Test main() with choice 1 (top states)"""
        with patch('os.makedirs'):
            with patch('builtins.input', return_value='1'):
                with patch('builtins.print') as mock_print:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with patch.object(JurisdictionResearcher, '__init__', lambda self: None):
                            researcher = JurisdictionResearcher()
                            researcher.base_dir = tmpdir
                            researcher.user_agent = 'Test'

                            # Patch the researcher instance used in main
                            with patch('datagod.scrapers.jurisdiction_research.JurisdictionResearcher') as MockResearcher:
                                mock_instance = MagicMock()
                                mock_instance.base_dir = tmpdir
                                mock_instance.research_top_states.return_value = [
                                    Jurisdiction(name="Test", state="CA")
                                ]
                                MockResearcher.return_value = mock_instance

                                main()

                                mock_instance.research_top_states.assert_called_once()

    def test_main_choice_2(self):
        """Test main() with choice 2 (all states)"""
        with patch('builtins.input', return_value='2'):
            with patch('builtins.print'):
                with patch('datagod.scrapers.jurisdiction_research.JurisdictionResearcher') as MockResearcher:
                    mock_instance = MagicMock()
                    mock_instance.base_dir = 'test'
                    mock_instance.research_all_states.return_value = []
                    MockResearcher.return_value = mock_instance

                    main()

                    mock_instance.research_all_states.assert_called_once()

    def test_main_choice_3(self):
        """Test main() with choice 3 (exit)"""
        with patch('builtins.input', return_value='3'):
            with patch('builtins.print') as mock_print:
                with patch('datagod.scrapers.jurisdiction_research.JurisdictionResearcher') as MockResearcher:
                    main()

                    # Should print exit message
                    exit_called = any('Exiting' in str(call) for call in mock_print.call_args_list)
                    assert exit_called

    def test_main_invalid_choice(self):
        """Test main() with invalid choice"""
        with patch('builtins.input', return_value='invalid'):
            with patch('builtins.print') as mock_print:
                with patch('datagod.scrapers.jurisdiction_research.JurisdictionResearcher') as MockResearcher:
                    main()

                    # Should print invalid choice message
                    invalid_called = any('Invalid' in str(call) for call in mock_print.call_args_list)
                    assert invalid_called


class TestJurisdictionDataclassEdgeCases:
    """Additional edge case tests for Jurisdiction dataclass"""

    def test_jurisdiction_with_special_characters_in_name(self):
        """Test jurisdiction with special characters in name"""
        j = Jurisdiction(
            name="St. Louis County, MO",
            state="MO",
            county="St. Louis"
        )
        assert j.name == "St. Louis County, MO"
        assert j.county == "St. Louis"

    def test_jurisdiction_with_apostrophe(self):
        """Test jurisdiction with apostrophe in name"""
        j = Jurisdiction(
            name="Prince George's County, MD",
            state="MD",
            county="Prince George's"
        )
        assert "'" in j.name

    def test_jurisdiction_with_hyphen(self):
        """Test jurisdiction with hyphen in name"""
        j = Jurisdiction(
            name="Miami-Dade County, FL",
            state="FL",
            county="Miami-Dade"
        )
        assert "-" in j.name


class TestResearcherLogging:
    """Tests for logging functionality"""

    def test_research_top_states_logs_progress(self):
        """Test that research_top_states logs progress"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir

                with patch.object(logger, 'info') as mock_logger:
                    researcher.research_top_states(['CA'])

                    # Should log at least once for the state
                    assert mock_logger.call_count >= 1

    def test_fetch_counties_logs_error_on_exception(self):
        """Test that fetch_state_counties logs errors"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with patch('requests.get', side_effect=Exception("Test error")):
                with patch.object(logger, 'error') as mock_logger:
                    researcher.fetch_state_counties('CA')
                    mock_logger.assert_called_once()


class TestResearcherIntegration:
    """Integration tests combining multiple methods"""

    def test_full_research_workflow(self):
        """Test full research workflow from start to finish"""
        with patch('os.makedirs'):
            researcher = JurisdictionResearcher()

            with tempfile.TemporaryDirectory() as tmpdir:
                researcher.base_dir = tmpdir

                # Get states
                states = researcher.get_state_list()
                assert len(states) > 0

                # Get counties for one state
                ca_counties = researcher.fetch_state_counties('CA')
                assert len(ca_counties) > 0

                # Research jurisdictions
                jurisdictions = []
                for county in ca_counties[:3]:  # Just first 3
                    j = researcher.research_jurisdiction('CA', county['name'])
                    jurisdictions.append(j)

                assert len(jurisdictions) == 3

                # Save data
                researcher.save_jurisdiction_data(jurisdictions, 'integration_test.csv')

                # Verify files exist
                assert os.path.exists(os.path.join(tmpdir, 'integration_test.csv'))
                assert os.path.exists(os.path.join(tmpdir, 'integration_test.json'))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
