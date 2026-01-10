"""
Pytest configuration and fixtures for DataGod tests
"""

import pytest
import os
import sys
from typing import Generator, Dict, Any
from datetime import datetime
from unittest.mock import MagicMock, patch

# Test database URL (SQLite in memory for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Set test environment
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TESTING"] = "1"


@pytest.fixture(autouse=True)
def clean_module_imports():
    """
    Clean up imported modules between tests to prevent test pollution.
    This is especially important for modules with global state.
    """
    # Capture modules before test
    modules_before = set(sys.modules.keys())

    yield

    # Clean up modules that were imported during the test
    modules_to_clean = [
        'main',
        'db_manager',
    ]

    for module in modules_to_clean:
        if module in sys.modules:
            del sys.modules[module]


@pytest.fixture(autouse=True)
def reset_api_manager():
    """Reset the global API manager instance between tests"""
    yield

    # Clean up the global API manager
    try:
        from datagod.scrapers import api_manager
        if hasattr(api_manager, 'api_manager'):
            # Reset the singleton
            api_manager.api_manager.active_integrations.clear()
            api_manager.api_manager.usage_stats = {
                'total_requests': 0,
                'total_cost': 0.0,
                'api_usage': {},
                'last_updated': datetime.now().isoformat()
            }
    except ImportError:
        pass


@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    from sqlalchemy import create_engine
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables"""
    # Import from __init__.py which has all models registered with Base
    from datagod.models import Base, Jurisdiction, Record, Entity, Relationship, DataSource
    from datagod.models.user import User
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Create a database session for tests with proper cleanup"""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    # Create a connection with a transaction that we'll rollback
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to the connection
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Rollback everything - this ensures test isolation
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_jurisdiction_data() -> Dict[str, Any]:
    """Sample jurisdiction data for testing"""
    return {
        "name": "Test County",
        "state": "TX",
        "county": "Test",
        "type": "county",
        "api_available": True,
        "scraper_needed": True,
        "population": 100000,
        "description": "Test jurisdiction for testing"
    }


@pytest.fixture
def sample_record_data() -> Dict[str, Any]:
    """Sample record data for testing - requires jurisdiction_id and data_source_id to be set"""
    return {
        "record_type": "mortgage",
        "record_id": "TEST-123456",
        "title": "Test Mortgage Record",
        "grantor": "John Doe",
        "grantee": "Bank of Test",
        "amount": 250000.00,
        "address": "123 Test Street",
        "city": "Test City",
        "state": "TX",
        "zip_code": "75001",
        "date": datetime.now(),
        "document_number": "DOC-789",
        "book_page": "100/50",
        "raw_data": {"test": "data"}
        # NOTE: jurisdiction_id and data_source_id must be set by the test
    }


@pytest.fixture
def sample_entity_data() -> Dict[str, Any]:
    """Sample entity data for testing"""
    return {
        "entity_name": "Test Corporation LLC",
        "entity_type": "company",
        "address": "456 Business Ave",
        "city": "Test City",
        "state": "TX",
        "zip_code": "75001",
        "status": "active"
    }


@pytest.fixture
def mock_api_response():
    """Mock API response for testing scrapers"""
    return {
        "properties": [
            {
                "parcel_number": "12345678",
                "owner_name": "John Smith",
                "situs_address": "123 Main St",
                "city": "Houston",
                "zip_code": "77001",
                "assessed_value": 350000,
                "land_value": 100000,
                "improvement_value": 250000
            }
        ],
        "total_count": 1
    }


@pytest.fixture
def mock_requests():
    """Mock requests library for API testing"""
    with patch('requests.Session') as mock:
        session = MagicMock()
        mock.return_value = session
        yield session


@pytest.fixture
def api_config() -> Dict[str, Any]:
    """Sample API configuration"""
    return {
        "jurisdiction_name": "Harris County",
        "api_key": "test_api_key",
        "requests_per_minute": 60,
        "timeout": 30
    }
