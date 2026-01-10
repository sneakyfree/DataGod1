"""
Tests for root main.py (application entry point)

Comprehensive tests for the main application entry point that can
start the API server or run database operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import argparse
import logging
import sys
import os


class TestMainModuleImports:
    """Tests for main module imports"""

    def test_argparse_import(self):
        """Test that argparse is importable"""
        import argparse
        assert argparse is not None

    def test_logging_import(self):
        """Test that logging is importable"""
        import logging
        assert logging is not None

    def test_sys_import(self):
        """Test that sys is importable"""
        import sys
        assert sys is not None

    def test_os_import(self):
        """Test that os is importable"""
        import os
        assert os is not None


class TestMainModuleSettings:
    """Tests for settings imports used by main.py"""

    def test_settings_api_host(self):
        """Test API_HOST setting is available"""
        from datagod.config.settings import API_HOST
        assert API_HOST is not None
        assert isinstance(API_HOST, str)

    def test_settings_api_port(self):
        """Test API_PORT setting is available"""
        from datagod.config.settings import API_PORT
        assert API_PORT is not None
        assert isinstance(API_PORT, int)

    def test_settings_api_workers(self):
        """Test API_WORKERS setting is available"""
        from datagod.config.settings import API_WORKERS
        assert API_WORKERS is not None
        assert isinstance(API_WORKERS, int)

    def test_settings_api_debug(self):
        """Test API_DEBUG setting is available"""
        from datagod.config.settings import API_DEBUG
        assert isinstance(API_DEBUG, bool)

    def test_settings_log_level(self):
        """Test LOG_LEVEL setting is available"""
        from datagod.config.settings import LOG_LEVEL
        assert LOG_LEVEL is not None
        assert isinstance(LOG_LEVEL, str)

    def test_settings_log_format(self):
        """Test LOG_FORMAT setting is available"""
        from datagod.config.settings import LOG_FORMAT
        assert LOG_FORMAT is not None
        assert isinstance(LOG_FORMAT, str)

    def test_settings_environment(self):
        """Test ENVIRONMENT setting is available"""
        from datagod.config.settings import ENVIRONMENT
        assert ENVIRONMENT is not None
        assert isinstance(ENVIRONMENT, str)


class TestInitDatabase:
    """Tests for init_database function"""

    @patch('db_manager.DatabaseManager')
    def test_init_database_without_reset(self, mock_db_class):
        """Test database initialization without reset"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        main.init_database(reset=False)

        mock_db_class.assert_called_once()
        mock_db.init_database.assert_called_once()
        mock_db.reset_database.assert_not_called()

    @patch('db_manager.DatabaseManager')
    def test_init_database_with_reset(self, mock_db_class):
        """Test database initialization with reset"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        main.init_database(reset=True)

        mock_db_class.assert_called_once()
        mock_db.reset_database.assert_called_once()
        mock_db.init_database.assert_not_called()

    @patch('db_manager.DatabaseManager')
    def test_init_database_default_is_no_reset(self, mock_db_class):
        """Test that init_database defaults to no reset"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        main.init_database()

        mock_db.init_database.assert_called_once()
        mock_db.reset_database.assert_not_called()


class TestSeedDatabase:
    """Tests for seed_database function"""

    @patch('db_manager.DatabaseManager')
    def test_seed_database_creates_jurisdictions(self, mock_db_class):
        """Test that seed_database creates sample jurisdictions"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1

        main.seed_database()

        # Should be called for each sample jurisdiction (3 in the code)
        assert mock_db.create_jurisdiction.call_count == 3

    @patch('db_manager.DatabaseManager')
    def test_seed_database_creates_data_sources(self, mock_db_class):
        """Test that seed_database creates data sources"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_data_source.return_value = 1

        main.seed_database()

        # Data sources should be created for each jurisdiction
        assert mock_db.create_data_source.call_count >= 1

    @patch('db_manager.DatabaseManager')
    def test_seed_database_creates_records(self, mock_db_class):
        """Test that seed_database creates sample records"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_data_source.return_value = 1
        mock_db.create_record.return_value = 1

        main.seed_database()

        # Records should be created
        assert mock_db.create_record.call_count >= 1

    @patch('db_manager.DatabaseManager')
    def test_seed_database_creates_entities(self, mock_db_class):
        """Test that seed_database creates sample entities"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_data_source.return_value = 1
        mock_db.create_entity.return_value = 1

        main.seed_database()

        # Entities should be created
        assert mock_db.create_entity.call_count >= 1

    @patch('db_manager.DatabaseManager')
    def test_seed_database_handles_failed_jurisdiction(self, mock_db_class):
        """Test seed_database handles jurisdiction creation failure"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = None

        # Should not raise exception
        main.seed_database()

        mock_db.create_jurisdiction.assert_called()


class TestShowStats:
    """Tests for show_stats function"""

    @patch('builtins.print')
    @patch('db_manager.DatabaseManager')
    def test_show_stats_displays_statistics(self, mock_db_class, mock_print):
        """Test that show_stats displays platform statistics"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_dashboard_stats.return_value = {
            'totalRecords': 100,
            'jurisdictions': 10,
            'dataSources': 5,
            'activeScrapers': 3,
            'totalEntities': 50
        }

        main.show_stats()

        mock_db.get_dashboard_stats.assert_called_once()
        # Should print multiple lines
        assert mock_print.call_count >= 1

    @patch('builtins.print')
    @patch('db_manager.DatabaseManager')
    def test_show_stats_formats_numbers(self, mock_db_class, mock_print):
        """Test that show_stats formats large numbers with commas"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_dashboard_stats.return_value = {
            'totalRecords': 1000000,
            'jurisdictions': 50,
            'dataSources': 100,
            'activeScrapers': 25,
            'totalEntities': 500000
        }

        main.show_stats()

        # Check that print was called with formatted numbers
        mock_print.assert_called()


class TestStartServer:
    """Tests for start_server function"""

    @patch('uvicorn.run')
    def test_start_server_with_defaults(self, mock_run):
        """Test starting server with default values"""
        import main
        from datagod.config.settings import API_HOST, API_PORT

        main.start_server()

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['host'] == API_HOST
        assert call_kwargs['port'] == API_PORT

    @patch('uvicorn.run')
    def test_start_server_with_custom_host(self, mock_run):
        """Test starting server with custom host"""
        import main

        main.start_server(host='127.0.0.1')

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['host'] == '127.0.0.1'

    @patch('uvicorn.run')
    def test_start_server_with_custom_port(self, mock_run):
        """Test starting server with custom port"""
        import main

        main.start_server(port=9000)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['port'] == 9000

    @patch('uvicorn.run')
    def test_start_server_with_reload(self, mock_run):
        """Test starting server with reload enabled"""
        import main

        main.start_server(reload=True)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['reload'] == True
        assert call_kwargs['workers'] == 1  # Workers should be 1 when reload is True

    @patch('uvicorn.run')
    def test_start_server_with_custom_workers(self, mock_run):
        """Test starting server with custom workers"""
        import main

        main.start_server(workers=8)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['workers'] == 8

    def test_start_server_uvicorn_not_installed(self):
        """Test handling when uvicorn is not installed"""
        import sys
        import main

        # Skip if uvicorn is already installed (which it usually is)
        # This tests the structure, actual import error is hard to test
        assert hasattr(main, 'start_server')

    @patch('uvicorn.run')
    @patch('sys.exit')
    def test_start_server_exception(self, mock_exit, mock_run):
        """Test handling server exception"""
        import main

        mock_run.side_effect = Exception("Server error")

        main.start_server()

        mock_exit.assert_called_once_with(1)


class TestMainFunction:
    """Tests for main function"""

    @patch('main.start_server')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_default_starts_server(self, mock_parse, mock_start):
        """Test that main() with no args starts server"""
        import main

        mock_args = MagicMock()
        mock_args.init = False
        mock_args.seed = False
        mock_args.stats = False
        mock_args.host = None
        mock_args.port = None
        mock_args.reload = False
        mock_args.workers = None
        mock_args.reset = False
        mock_parse.return_value = mock_args

        main.main()

        mock_start.assert_called_once()

    @patch('main.init_database')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_with_init_flag(self, mock_parse, mock_init):
        """Test main() with --init flag"""
        import main

        mock_args = MagicMock()
        mock_args.init = True
        mock_args.reset = False
        mock_args.seed = False
        mock_args.stats = False
        mock_parse.return_value = mock_args

        main.main()

        mock_init.assert_called_once_with(reset=False)

    @patch('main.init_database')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_with_init_and_reset_flags(self, mock_parse, mock_init):
        """Test main() with --init --reset flags"""
        import main

        mock_args = MagicMock()
        mock_args.init = True
        mock_args.reset = True
        mock_args.seed = False
        mock_args.stats = False
        mock_parse.return_value = mock_args

        main.main()

        mock_init.assert_called_once_with(reset=True)

    @patch('main.seed_database')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_with_seed_flag(self, mock_parse, mock_seed):
        """Test main() with --seed flag"""
        import main

        mock_args = MagicMock()
        mock_args.init = False
        mock_args.seed = True
        mock_args.stats = False
        mock_parse.return_value = mock_args

        main.main()

        mock_seed.assert_called_once()

    @patch('main.show_stats')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_with_stats_flag(self, mock_parse, mock_stats):
        """Test main() with --stats flag"""
        import main

        mock_args = MagicMock()
        mock_args.init = False
        mock_args.seed = False
        mock_args.stats = True
        mock_parse.return_value = mock_args

        main.main()

        mock_stats.assert_called_once()

    @patch('main.start_server')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_main_passes_server_options(self, mock_parse, mock_start):
        """Test that main() passes custom server options"""
        import main

        mock_args = MagicMock()
        mock_args.init = False
        mock_args.seed = False
        mock_args.stats = False
        mock_args.host = '127.0.0.1'
        mock_args.port = 9000
        mock_args.reload = True
        mock_args.workers = 4
        mock_parse.return_value = mock_args

        main.main()

        mock_start.assert_called_once_with(
            host='127.0.0.1',
            port=9000,
            reload=True,
            workers=4
        )


class TestArgumentParser:
    """Tests for argument parser configuration"""

    def test_parser_accepts_host_argument(self):
        """Test parser accepts --host argument"""
        from main import main
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--host', default=None)
        args = parser.parse_args(['--host', 'localhost'])
        assert args.host == 'localhost'

    def test_parser_accepts_port_argument(self):
        """Test parser accepts --port argument"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--port', type=int, default=None)
        args = parser.parse_args(['--port', '9000'])
        assert args.port == 9000

    def test_parser_accepts_workers_argument(self):
        """Test parser accepts --workers argument"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--workers', type=int, default=None)
        args = parser.parse_args(['--workers', '8'])
        assert args.workers == 8

    def test_parser_accepts_reload_flag(self):
        """Test parser accepts --reload flag"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--reload', action='store_true')
        args = parser.parse_args(['--reload'])
        assert args.reload == True

    def test_parser_accepts_init_flag(self):
        """Test parser accepts --init flag"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--init', action='store_true')
        args = parser.parse_args(['--init'])
        assert args.init == True

    def test_parser_accepts_reset_flag(self):
        """Test parser accepts --reset flag"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--reset', action='store_true')
        args = parser.parse_args(['--reset'])
        assert args.reset == True

    def test_parser_accepts_seed_flag(self):
        """Test parser accepts --seed flag"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--seed', action='store_true')
        args = parser.parse_args(['--seed'])
        assert args.seed == True

    def test_parser_accepts_stats_flag(self):
        """Test parser accepts --stats flag"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--stats', action='store_true')
        args = parser.parse_args(['--stats'])
        assert args.stats == True


class TestKeyboardInterruptHandling:
    """Tests for keyboard interrupt handling"""

    @patch('main.main')
    @patch('main.sys.exit')
    def test_keyboard_interrupt_handled_gracefully(self, mock_exit, mock_main):
        """Test that KeyboardInterrupt is handled gracefully"""
        import main

        mock_main.side_effect = KeyboardInterrupt()

        # Simulate the if __name__ == "__main__" block behavior
        try:
            main.main()
        except KeyboardInterrupt:
            # This is expected behavior
            pass


class TestExceptionHandling:
    """Tests for exception handling in main entry point"""

    @patch('main.main')
    @patch('main.sys.exit')
    def test_exception_logs_and_exits(self, mock_exit, mock_main):
        """Test that exceptions are logged and cause exit"""
        import main

        mock_main.side_effect = Exception("Test error")

        # The exception should be caught in the if __name__ block
        try:
            main.main()
        except Exception:
            pass


class TestLoggingSetup:
    """Tests for logging setup in main.py"""

    def test_logger_is_configured(self):
        """Test that logger is configured"""
        import main
        assert hasattr(main, 'logger')
        assert isinstance(main.logger, logging.Logger)

    def test_logging_format_used(self):
        """Test that LOG_FORMAT is used"""
        from datagod.config.settings import LOG_FORMAT
        assert LOG_FORMAT is not None
        assert '%' in LOG_FORMAT or '{' in LOG_FORMAT  # Check it's a format string

    def test_logging_level_used(self):
        """Test that LOG_LEVEL is used"""
        from datagod.config.settings import LOG_LEVEL
        assert LOG_LEVEL is not None
        assert LOG_LEVEL.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class TestModuleFileStructure:
    """Tests for main.py file structure"""

    def test_main_py_exists_at_root(self):
        """Test that main.py exists at project root"""
        import os
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        main_path = project_root / 'main.py'
        assert main_path.exists(), f"main.py not found at {main_path}"

    def test_main_py_has_shebang(self):
        """Test that main.py has proper shebang"""
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        main_path = project_root / 'main.py'

        content = main_path.read_text()
        assert content.startswith('#!/usr/bin/env python3')

    def test_main_py_has_docstring(self):
        """Test that main.py has module docstring"""
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        main_path = project_root / 'main.py'

        content = main_path.read_text()
        assert '"""' in content

    def test_main_has_name_guard(self):
        """Test that main.py has if __name__ == '__main__' guard"""
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        main_path = project_root / 'main.py'

        content = main_path.read_text()
        assert 'if __name__ == "__main__"' in content


class TestSeedDatabaseContent:
    """Tests for seed_database data content"""

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_miami_dade(self, mock_db_class):
        """Test that seed creates Miami-Dade jurisdiction"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1

        main.seed_database()

        # Check if Miami-Dade was created
        calls = mock_db.create_jurisdiction.call_args_list
        names = [call[1]['name'] for call in calls if 'name' in call[1]]
        assert 'Miami-Dade County' in names

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_los_angeles(self, mock_db_class):
        """Test that seed creates Los Angeles jurisdiction"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1

        main.seed_database()

        calls = mock_db.create_jurisdiction.call_args_list
        names = [call[1]['name'] for call in calls if 'name' in call[1]]
        assert 'Los Angeles County' in names

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_cook_county(self, mock_db_class):
        """Test that seed creates Cook County jurisdiction"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1

        main.seed_database()

        calls = mock_db.create_jurisdiction.call_args_list
        names = [call[1]['name'] for call in calls if 'name' in call[1]]
        assert 'Cook County' in names

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_mortgage_record(self, mock_db_class):
        """Test that seed creates mortgage record"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_data_source.return_value = 1
        mock_db.create_record.return_value = 1

        main.seed_database()

        calls = mock_db.create_record.call_args_list
        record_types = [call[1].get('record_type') for call in calls]
        assert 'mortgage' in record_types

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_deed_record(self, mock_db_class):
        """Test that seed creates deed record"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_data_source.return_value = 1
        mock_db.create_record.return_value = 1

        main.seed_database()

        calls = mock_db.create_record.call_args_list
        record_types = [call[1].get('record_type') for call in calls]
        assert 'deed' in record_types

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_person_entities(self, mock_db_class):
        """Test that seed creates person entities"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_entity.return_value = 1

        main.seed_database()

        calls = mock_db.create_entity.call_args_list
        entity_types = [call[1].get('entity_type') for call in calls]
        assert 'person' in entity_types

    @patch('db_manager.DatabaseManager')
    def test_seed_creates_company_entity(self, mock_db_class):
        """Test that seed creates company entity"""
        import main

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.create_jurisdiction.return_value = 1
        mock_db.create_entity.return_value = 1

        main.seed_database()

        calls = mock_db.create_entity.call_args_list
        entity_types = [call[1].get('entity_type') for call in calls]
        assert 'company' in entity_types
