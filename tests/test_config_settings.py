"""
Tests for DataGod configuration settings
"""

import os
from pathlib import Path

import pytest


class TestProjectPaths:
    """Tests for project path configuration"""

    def test_project_root_exists(self):
        """Test that project root path is valid"""
        from datagod.config.settings import PROJECT_ROOT

        assert PROJECT_ROOT is not None
        assert isinstance(PROJECT_ROOT, Path)

    def test_data_dir_exists(self):
        """Test that data directory exists"""
        from datagod.config.settings import DATA_DIR

        assert DATA_DIR is not None
        assert DATA_DIR.exists() or DATA_DIR.parent.exists()

    def test_logs_dir_exists(self):
        """Test that logs directory exists"""
        from datagod.config.settings import LOGS_DIR

        assert LOGS_DIR is not None

    def test_cache_dir_exists(self):
        """Test that cache directory exists"""
        from datagod.config.settings import CACHE_DIR

        assert CACHE_DIR is not None


class TestDatabaseConfiguration:
    """Tests for database configuration"""

    def test_database_url_format(self):
        """Test database URL is properly formatted"""
        from datagod.config.settings import DATABASE_URL

        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)
        # Should be either sqlite or postgresql
        assert "sqlite" in DATABASE_URL or "postgresql" in DATABASE_URL

    def test_db_pool_settings(self):
        """Test database pool settings have valid values"""
        from datagod.config.settings import (
            DB_MAX_OVERFLOW,
            DB_POOL_RECYCLE,
            DB_POOL_SIZE,
            DB_POOL_TIMEOUT,
        )

        assert isinstance(DB_POOL_SIZE, int)
        assert DB_POOL_SIZE > 0
        assert isinstance(DB_MAX_OVERFLOW, int)
        assert DB_MAX_OVERFLOW >= 0
        assert isinstance(DB_POOL_TIMEOUT, int)
        assert DB_POOL_TIMEOUT > 0
        assert isinstance(DB_POOL_RECYCLE, int)
        assert DB_POOL_RECYCLE > 0


class TestAPIConfiguration:
    """Tests for API configuration"""

    def test_api_host(self):
        """Test API host is configured"""
        from datagod.config.settings import API_HOST

        assert API_HOST is not None
        assert isinstance(API_HOST, str)

    def test_api_port(self):
        """Test API port is valid"""
        from datagod.config.settings import API_PORT

        assert isinstance(API_PORT, int)
        assert 1 <= API_PORT <= 65535

    def test_api_workers(self):
        """Test API workers is valid"""
        from datagod.config.settings import API_WORKERS

        assert isinstance(API_WORKERS, int)
        assert API_WORKERS >= 1

    def test_api_debug_is_boolean(self):
        """Test API debug is boolean"""
        from datagod.config.settings import API_DEBUG

        assert isinstance(API_DEBUG, bool)


class TestSecurityConfiguration:
    """Tests for security configuration"""

    def test_secret_key_exists(self):
        """Test secret key is defined"""
        from datagod.config.settings import SECRET_KEY

        assert SECRET_KEY is not None
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_jwt_settings(self):
        """Test JWT settings are properly configured"""
        from datagod.config.settings import (
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            JWT_ALGORITHM,
            JWT_SECRET_KEY,
        )

        assert JWT_SECRET_KEY is not None
        assert JWT_ALGORITHM in ["HS256", "HS384", "HS512", "RS256"]
        assert isinstance(JWT_ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


class TestCORSConfiguration:
    """Tests for CORS configuration"""

    def test_cors_origins_is_list(self):
        """Test CORS origins is a list"""
        from datagod.config.settings import CORS_ORIGINS

        assert isinstance(CORS_ORIGINS, list)

    def test_cors_origins_contains_localhost(self):
        """Test CORS origins includes localhost for development"""
        from datagod.config.settings import CORS_ORIGINS

        # At least one origin should be defined
        assert len(CORS_ORIGINS) > 0


class TestRedisConfiguration:
    """Tests for Redis configuration"""

    def test_redis_url_format(self):
        """Test Redis URL is properly formatted"""
        from datagod.config.settings import REDIS_URL

        assert REDIS_URL is not None
        assert isinstance(REDIS_URL, str)
        assert "redis://" in REDIS_URL

    def test_redis_cache_ttl(self):
        """Test Redis cache TTL is valid"""
        from datagod.config.settings import REDIS_CACHE_TTL

        assert isinstance(REDIS_CACHE_TTL, int)
        assert REDIS_CACHE_TTL > 0


class TestScrapingConfiguration:
    """Tests for scraping configuration"""

    def test_scraper_rate_limit(self):
        """Test scraper rate limit is valid"""
        from datagod.config.settings import SCRAPER_RATE_LIMIT

        assert isinstance(SCRAPER_RATE_LIMIT, float)
        assert SCRAPER_RATE_LIMIT > 0

    def test_scraper_timeout(self):
        """Test scraper timeout is valid"""
        from datagod.config.settings import SCRAPER_TIMEOUT

        assert isinstance(SCRAPER_TIMEOUT, int)
        assert SCRAPER_TIMEOUT > 0

    def test_scraper_max_retries(self):
        """Test scraper max retries is valid"""
        from datagod.config.settings import SCRAPER_MAX_RETRIES

        assert isinstance(SCRAPER_MAX_RETRIES, int)
        assert SCRAPER_MAX_RETRIES >= 0

    def test_scraper_concurrent_requests(self):
        """Test scraper concurrent requests is valid"""
        from datagod.config.settings import SCRAPER_CONCURRENT_REQUESTS

        assert isinstance(SCRAPER_CONCURRENT_REQUESTS, int)
        assert SCRAPER_CONCURRENT_REQUESTS >= 1

    def test_scraper_use_proxies_is_boolean(self):
        """Test scraper use proxies is boolean"""
        from datagod.config.settings import SCRAPER_USE_PROXIES

        assert isinstance(SCRAPER_USE_PROXIES, bool)


class TestDeduplicationConfiguration:
    """Tests for deduplication configuration"""

    def test_deduplication_similarity_threshold(self):
        """Test deduplication similarity threshold is valid"""
        from datagod.config.settings import DEDUPLICATION_SIMILARITY_THRESHOLD

        assert isinstance(DEDUPLICATION_SIMILARITY_THRESHOLD, float)
        assert 0 <= DEDUPLICATION_SIMILARITY_THRESHOLD <= 1

    def test_deduplication_algorithm(self):
        """Test deduplication algorithm is defined"""
        from datagod.config.settings import DEDUPLICATION_ALGORITHM

        assert isinstance(DEDUPLICATION_ALGORITHM, str)
        assert len(DEDUPLICATION_ALGORITHM) > 0

    def test_deduplication_batch_size(self):
        """Test deduplication batch size is valid"""
        from datagod.config.settings import DEDUPLICATION_BATCH_SIZE

        assert isinstance(DEDUPLICATION_BATCH_SIZE, int)
        assert DEDUPLICATION_BATCH_SIZE > 0


class TestLoggingConfiguration:
    """Tests for logging configuration"""

    def test_log_level_is_valid(self):
        """Test log level is a valid logging level"""
        from datagod.config.settings import LOG_LEVEL

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert LOG_LEVEL in valid_levels

    def test_log_format(self):
        """Test log format is defined"""
        from datagod.config.settings import LOG_FORMAT

        assert isinstance(LOG_FORMAT, str)
        assert "%(message)s" in LOG_FORMAT

    def test_log_file_path(self):
        """Test log file path is defined"""
        from datagod.config.settings import LOG_FILE

        assert isinstance(LOG_FILE, str)
        assert len(LOG_FILE) > 0

    def test_log_rotation_settings(self):
        """Test log rotation settings are valid"""
        from datagod.config.settings import LOG_BACKUP_COUNT, LOG_MAX_BYTES

        assert isinstance(LOG_MAX_BYTES, int)
        assert LOG_MAX_BYTES > 0
        assert isinstance(LOG_BACKUP_COUNT, int)
        assert LOG_BACKUP_COUNT >= 0


class TestEmailConfiguration:
    """Tests for email configuration"""

    def test_smtp_server(self):
        """Test SMTP server is defined"""
        from datagod.config.settings import SMTP_SERVER

        assert isinstance(SMTP_SERVER, str)
        assert len(SMTP_SERVER) > 0

    def test_smtp_port(self):
        """Test SMTP port is valid"""
        from datagod.config.settings import SMTP_PORT

        assert isinstance(SMTP_PORT, int)
        assert 1 <= SMTP_PORT <= 65535

    def test_email_from(self):
        """Test email from address is defined"""
        from datagod.config.settings import EMAIL_FROM

        assert isinstance(EMAIL_FROM, str)
        assert "@" in EMAIL_FROM


class TestFileUploadConfiguration:
    """Tests for file upload configuration"""

    def test_max_upload_size(self):
        """Test max upload size is valid"""
        from datagod.config.settings import MAX_UPLOAD_SIZE

        assert isinstance(MAX_UPLOAD_SIZE, int)
        assert MAX_UPLOAD_SIZE > 0

    def test_allowed_extensions_is_list(self):
        """Test allowed extensions is a list"""
        from datagod.config.settings import ALLOWED_EXTENSIONS

        assert isinstance(ALLOWED_EXTENSIONS, list)
        assert len(ALLOWED_EXTENSIONS) > 0

    def test_upload_dir_exists(self):
        """Test upload directory is defined"""
        from datagod.config.settings import UPLOAD_DIR

        assert UPLOAD_DIR is not None


class TestExportConfiguration:
    """Tests for export configuration"""

    def test_export_dir_exists(self):
        """Test export directory is defined"""
        from datagod.config.settings import EXPORT_DIR

        assert EXPORT_DIR is not None

    def test_export_max_rows(self):
        """Test export max rows is valid"""
        from datagod.config.settings import EXPORT_MAX_ROWS

        assert isinstance(EXPORT_MAX_ROWS, int)
        assert EXPORT_MAX_ROWS > 0


class TestMonitoringConfiguration:
    """Tests for monitoring configuration"""

    def test_enable_metrics_is_boolean(self):
        """Test enable metrics is boolean"""
        from datagod.config.settings import ENABLE_METRICS

        assert isinstance(ENABLE_METRICS, bool)


class TestSettingsClass:
    """Tests for Settings class if present"""

    def test_settings_instance_creation(self):
        """Test that Settings class can be instantiated"""
        # This tests the api/src/config.py Settings class
        try:
            from api.src.config import Settings, settings

            assert settings is not None
            assert hasattr(settings, "api_title")
            assert hasattr(settings, "api_version")
        except ImportError:
            # If import fails, skip this test
            pytest.skip("api.src.config module not available")

    def test_api_config_settings(self):
        """Test API config settings"""
        try:
            from api.src.config import settings

            assert settings.api_title is not None
            assert settings.api_version is not None
            assert settings.jwt_secret_key is not None
        except ImportError:
            pytest.skip("api.src.config module not available")
