"""
Comprehensive tests for cli.py module
"""

import pytest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from io import StringIO
import argparse


class TestCLIImports:
    """Tests for CLI module imports"""

    def test_cli_module_import(self):
        """Test CLI module can be imported"""
        import cli
        assert cli is not None

    def test_init_database_import(self):
        """Test init_database function can be imported"""
        from cli import init_database
        assert init_database is not None
        assert callable(init_database)

    def test_serve_api_import(self):
        """Test serve_api function can be imported"""
        from cli import serve_api
        assert serve_api is not None
        assert callable(serve_api)

    def test_run_scraper_import(self):
        """Test run_scraper function can be imported"""
        from cli import run_scraper
        assert run_scraper is not None
        assert callable(run_scraper)

    def test_search_records_import(self):
        """Test search_records function can be imported"""
        from cli import search_records
        assert search_records is not None
        assert callable(search_records)

    def test_show_stats_import(self):
        """Test show_stats function can be imported"""
        from cli import show_stats
        assert show_stats is not None
        assert callable(show_stats)

    def test_seed_data_import(self):
        """Test seed_data function can be imported"""
        from cli import seed_data
        assert seed_data is not None
        assert callable(seed_data)

    def test_export_data_import(self):
        """Test export_data function can be imported"""
        from cli import export_data
        assert export_data is not None
        assert callable(export_data)

    def test_list_jurisdictions_import(self):
        """Test list_jurisdictions function can be imported"""
        from cli import list_jurisdictions
        assert list_jurisdictions is not None
        assert callable(list_jurisdictions)

    def test_add_jurisdiction_import(self):
        """Test add_jurisdiction function can be imported"""
        from cli import add_jurisdiction
        assert add_jurisdiction is not None
        assert callable(add_jurisdiction)

    def test_main_import(self):
        """Test main function can be imported"""
        from cli import main
        assert main is not None
        assert callable(main)


class TestInitDatabase:
    """Tests for init_database command"""

    def test_init_database_success(self):
        """Test init_database successful initialization"""
        from cli import init_database

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.init_database.return_value = True
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.reset = False

            with patch('builtins.print'):
                init_database(args)

            mock_db.init_database.assert_called_once()

    def test_init_database_failure(self):
        """Test init_database failure"""
        from cli import init_database

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.init_database.return_value = False
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.reset = False

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    init_database(args)

            assert exc_info.value.code == 1

    def test_init_database_reset_confirm(self):
        """Test init_database reset with confirmation"""
        from cli import init_database

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.reset = True

            with patch('builtins.input', return_value='yes'):
                with patch('builtins.print'):
                    init_database(args)

            mock_db.reset_database.assert_called_once()

    def test_init_database_reset_cancel(self):
        """Test init_database reset cancelled"""
        from cli import init_database

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.reset = True

            with patch('builtins.input', return_value='no'):
                with patch('builtins.print'):
                    init_database(args)

            mock_db.reset_database.assert_not_called()


class TestServeAPI:
    """Tests for serve_api command"""

    def test_serve_api_default(self):
        """Test serve_api with default arguments"""
        from cli import serve_api

        mock_uvicorn = MagicMock()

        with patch.dict('sys.modules', {'uvicorn': mock_uvicorn}):
            args = MagicMock()
            args.host = '0.0.0.0'
            args.port = 8000
            args.reload = False
            args.workers = 4

            with patch('builtins.print'):
                serve_api(args)

            mock_uvicorn.run.assert_called_once()

    def test_serve_api_with_reload(self):
        """Test serve_api with reload enabled"""
        from cli import serve_api

        mock_uvicorn = MagicMock()

        with patch.dict('sys.modules', {'uvicorn': mock_uvicorn}):
            args = MagicMock()
            args.host = '127.0.0.1'
            args.port = 8080
            args.reload = True
            args.workers = 2

            with patch('builtins.print'):
                serve_api(args)

            mock_uvicorn.run.assert_called_once()

    def test_serve_api_exception(self):
        """Test serve_api handles exceptions"""
        from cli import serve_api

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = Exception("Server error")

        with patch.dict('sys.modules', {'uvicorn': mock_uvicorn}):
            args = MagicMock()
            args.host = '0.0.0.0'
            args.port = 8000
            args.reload = False
            args.workers = 4

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    serve_api(args)

            assert exc_info.value.code == 1


class TestRunScraper:
    """Tests for run_scraper command"""

    def test_run_scraper_all(self):
        """Test run_scraper with --all flag"""
        from cli import run_scraper

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.list_jurisdictions.return_value = [
                {'name': 'County A', 'state': 'TX'},
                {'name': 'County B', 'state': 'CA'}
            ]
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.all = True
            args.jurisdiction_id = None

            with patch('builtins.print'):
                run_scraper(args)

            mock_db.list_jurisdictions.assert_called_once()

    def test_run_scraper_specific_jurisdiction(self):
        """Test run_scraper with specific jurisdiction"""
        from cli import run_scraper

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.get_jurisdiction.return_value = {'id': 1, 'name': 'Test County'}
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.all = False
            args.jurisdiction_id = 1

            with patch('builtins.print'):
                run_scraper(args)

            mock_db.get_jurisdiction.assert_called_once_with(1)

    def test_run_scraper_jurisdiction_not_found(self):
        """Test run_scraper with non-existent jurisdiction"""
        from cli import run_scraper

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.get_jurisdiction.return_value = None
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.all = False
            args.jurisdiction_id = 999

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    run_scraper(args)

            assert exc_info.value.code == 1

    def test_run_scraper_no_args(self):
        """Test run_scraper without required arguments"""
        from cli import run_scraper

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db_class.return_value = MagicMock()

            args = MagicMock()
            args.all = False
            args.jurisdiction_id = None

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    run_scraper(args)

            assert exc_info.value.code == 1


class TestSearchRecords:
    """Tests for search_records command"""

    def test_search_records_found(self):
        """Test search_records with results"""
        from cli import search_records

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.search_records.return_value = [
                {
                    'id': 1,
                    'title': 'Test Mortgage',
                    'record_type': 'mortgage',
                    'amount': 500000,
                    'date': '2024-01-15',
                    'grantor': 'John Doe',
                    'grantee': 'Bank'
                }
            ]
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.query = 'mortgage'
            args.type = None
            args.jurisdiction_id = None
            args.limit = 20

            with patch('builtins.print'):
                search_records(args)

            mock_db.search_records.assert_called_once()

    def test_search_records_not_found(self):
        """Test search_records with no results"""
        from cli import search_records

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.search_records.return_value = []
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.query = 'nonexistent'
            args.type = None
            args.jurisdiction_id = None
            args.limit = 20

            with patch('builtins.print') as mock_print:
                search_records(args)

            # Should print "No records found"
            mock_print.assert_called_with("No records found.")


class TestShowStats:
    """Tests for show_stats command"""

    def test_show_stats(self):
        """Test show_stats displays statistics"""
        from cli import show_stats

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.get_dashboard_stats.return_value = {
                'totalRecords': 1000,
                'jurisdictions': 50,
                'dataSources': 25,
                'activeScrapers': 10,
                'totalEntities': 5000,
                'recentRecords': [
                    {'title': 'Recent Record 1'},
                    {'title': 'Recent Record 2'}
                ]
            }
            mock_db_class.return_value = mock_db

            args = MagicMock()

            with patch('builtins.print'):
                show_stats(args)

            mock_db.get_dashboard_stats.assert_called_once()


class TestSeedData:
    """Tests for seed_data command"""

    def test_seed_data(self):
        """Test seed_data creates sample data"""
        from cli import seed_data

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.create_jurisdiction.return_value = 1
            mock_db.create_data_source.return_value = 1
            mock_db.create_record.return_value = 1
            mock_db.create_entity.return_value = 1
            mock_db_class.return_value = mock_db

            args = MagicMock()

            with patch('builtins.print'):
                seed_data(args)

            # Should create jurisdictions
            assert mock_db.create_jurisdiction.call_count >= 5

    def test_seed_data_no_jurisdictions_created(self):
        """Test seed_data when jurisdictions already exist"""
        from cli import seed_data

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.create_jurisdiction.return_value = None
            mock_db_class.return_value = mock_db

            args = MagicMock()

            with patch('builtins.print'):
                seed_data(args)


class TestExportData:
    """Tests for export_data command"""

    def test_export_data_json(self):
        """Test export_data to JSON format"""
        from cli import export_data

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.search_records.return_value = [
                {'id': 1, 'title': 'Record 1'},
                {'id': 2, 'title': 'Record 2'}
            ]
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.query = None
            args.type = None
            args.limit = None
            args.format = 'json'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                args.output = f.name

            try:
                with patch('builtins.print'):
                    export_data(args)

                # Verify file was created and contains JSON
                with open(args.output, 'r') as f:
                    data = json.load(f)
                    assert len(data) == 2
            finally:
                os.unlink(args.output)

    def test_export_data_csv(self):
        """Test export_data to CSV format"""
        from cli import export_data

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.search_records.return_value = [
                {'id': 1, 'title': 'Record 1'},
                {'id': 2, 'title': 'Record 2'}
            ]
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.query = None
            args.type = None
            args.limit = None
            args.format = 'csv'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                args.output = f.name

            try:
                with patch('builtins.print'):
                    export_data(args)

                # Verify file was created
                with open(args.output, 'r') as f:
                    content = f.read()
                    assert 'id' in content
                    assert 'title' in content
            finally:
                os.unlink(args.output)

    def test_export_data_no_records(self):
        """Test export_data with no records"""
        from cli import export_data

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.search_records.return_value = []
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.query = None
            args.type = None
            args.limit = None
            args.format = 'json'
            args.output = '/tmp/test.json'

            with patch('builtins.print') as mock_print:
                export_data(args)

            mock_print.assert_called_with("No records to export.")


class TestListJurisdictions:
    """Tests for list_jurisdictions command"""

    def test_list_jurisdictions(self):
        """Test list_jurisdictions displays jurisdictions"""
        from cli import list_jurisdictions

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.list_jurisdictions.return_value = [
                {'id': 1, 'name': 'County A', 'state': 'TX', 'type': 'county', 'api_available': True},
                {'id': 2, 'name': 'County B', 'state': 'CA', 'type': 'county', 'api_available': False}
            ]
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.state = None
            args.limit = 50

            with patch('builtins.print'):
                list_jurisdictions(args)

            mock_db.list_jurisdictions.assert_called_once()

    def test_list_jurisdictions_empty(self):
        """Test list_jurisdictions with no jurisdictions"""
        from cli import list_jurisdictions

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.list_jurisdictions.return_value = []
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.state = None
            args.limit = 50

            with patch('builtins.print') as mock_print:
                list_jurisdictions(args)

            mock_print.assert_called_with("No jurisdictions found.")


class TestAddJurisdiction:
    """Tests for add_jurisdiction command"""

    def test_add_jurisdiction_success(self):
        """Test add_jurisdiction successful creation"""
        from cli import add_jurisdiction

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.create_jurisdiction.return_value = 1
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.name = 'New County'
            args.state = 'TX'
            args.county = 'New County'
            args.type = 'county'
            args.api_available = False
            args.description = 'A new county'

            with patch('builtins.print'):
                add_jurisdiction(args)

            mock_db.create_jurisdiction.assert_called_once()

    def test_add_jurisdiction_failure(self):
        """Test add_jurisdiction failure"""
        from cli import add_jurisdiction

        with patch('db_manager.DatabaseManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.create_jurisdiction.return_value = None
            mock_db_class.return_value = mock_db

            args = MagicMock()
            args.name = 'Existing County'
            args.state = 'TX'
            args.county = 'Existing County'
            args.type = 'county'
            args.api_available = False
            args.description = None

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    add_jurisdiction(args)

            assert exc_info.value.code == 1


class TestMainFunction:
    """Tests for main function"""

    def test_main_no_command(self):
        """Test main with no command shows help"""
        from cli import main

        with patch('sys.argv', ['cli.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    @patch('cli.init_database')
    def test_main_init_command(self, mock_init):
        """Test main with init command"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'init']):
            main()

        mock_init.assert_called_once()

    @patch('cli.show_stats')
    def test_main_stats_command(self, mock_stats):
        """Test main with stats command"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'stats']):
            main()

        mock_stats.assert_called_once()

    @patch('cli.seed_data')
    def test_main_seed_command(self, mock_seed):
        """Test main with seed command"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'seed']):
            main()

        mock_seed.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test main handles keyboard interrupt"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'stats']):
            with patch('cli.show_stats', side_effect=KeyboardInterrupt):
                with patch('builtins.print'):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0

    def test_main_exception(self):
        """Test main handles exceptions"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'stats']):
            with patch('cli.show_stats', side_effect=Exception("Test error")):
                with patch('builtins.print'):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 1


class TestArgumentParsing:
    """Tests for argument parsing"""

    def test_init_parser_reset_flag(self):
        """Test init command reset flag"""
        from cli import main
        import argparse

        with patch('sys.argv', ['cli.py', 'init', '--reset']):
            with patch('cli.init_database') as mock_init:
                with patch('builtins.input', return_value='yes'):
                    main()

                args = mock_init.call_args[0][0]
                assert args.reset is True

    def test_serve_parser_options(self):
        """Test serve command options"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'serve', '--host', '127.0.0.1', '--port', '9000']):
            with patch('cli.serve_api') as mock_serve:
                main()

                args = mock_serve.call_args[0][0]
                assert args.host == '127.0.0.1'
                assert args.port == 9000

    def test_search_parser_options(self):
        """Test search command options"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'search', 'mortgage', '--type', 'deed', '--limit', '10']):
            with patch('cli.search_records') as mock_search:
                main()

                args = mock_search.call_args[0][0]
                assert args.query == 'mortgage'
                assert args.type == 'deed'
                assert args.limit == 10

    def test_export_parser_options(self):
        """Test export command options"""
        from cli import main

        with patch('sys.argv', ['cli.py', 'export', '-o', 'output.json', '--format', 'csv']):
            with patch('cli.export_data') as mock_export:
                main()

                args = mock_export.call_args[0][0]
                assert args.output == 'output.json'
                assert args.format == 'csv'
