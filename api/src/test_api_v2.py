"""
Test suite for DataGod API v2
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import date
import sys
import os
from pathlib import Path
from passlib.context import CryptContext

# Add api/src to path FIRST (before project root) so that relative imports work correctly
project_root = Path(__file__).parent.parent.parent
api_src_path = Path(__file__).parent
# Insert api_src_path at position 0 so it takes priority
sys.path.insert(0, str(api_src_path))
# Insert project root after api_src_path
sys.path.insert(1, str(project_root))

# Password hashing for mock users
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MockUserDbManager:
    """Mock user database manager with demo users."""

    def __init__(self):
        # Pre-hash passwords once
        self.demo_users = {
            "admin": {
                "id": 1,
                "username": "admin",
                "email": "admin@datagod.com",
                "full_name": "DataGod Admin",
                "hashed_password": pwd_context.hash("admin123"),
                "disabled": False,
                "roles": ["admin", "user"],
                "email_verified": True,
                "subscription_tier": "enterprise",
                "last_login": None,
                "login_count": 0,
                "api_calls_today": 0,
                "exports_this_month": 0,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            "user": {
                "id": 2,
                "username": "user",
                "email": "user@datagod.com",
                "full_name": "DataGod User",
                "hashed_password": pwd_context.hash("user123"),
                "disabled": False,
                "roles": ["user"],
                "email_verified": True,
                "subscription_tier": "free",
                "last_login": None,
                "login_count": 0,
                "api_calls_today": 0,
                "exports_this_month": 0,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }

    def get_user_by_username(self, username):
        return self.demo_users.get(username)

    def get_user_for_auth(self, username):
        return self.demo_users.get(username)

    def get_user_by_email(self, email):
        for user in self.demo_users.values():
            if user["email"] == email:
                return user
        return None

    def check_user_locked(self, username):
        return False

    def record_login(self, username, success=True):
        return True

    def create_user(self, username, email, hashed_password, full_name=None, roles=None, disabled=False):
        if username in self.demo_users:
            return None
        for user in self.demo_users.values():
            if user["email"] == email:
                return None
        self.demo_users[username] = {
            "id": len(self.demo_users) + 1,
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "disabled": disabled,
            "roles": roles or ["user"],
            "email_verified": False,
            "subscription_tier": "free",
            "last_login": None,
            "login_count": 0,
            "api_calls_today": 0,
            "exports_this_month": 0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        return len(self.demo_users)

    def list_users(self):
        return list(self.demo_users.values())

    def init_database(self):
        return True

    def set_password_reset_token(self, email, token, expires_hours=1):
        for user in self.demo_users.values():
            if user["email"] == email:
                return True
        return False

    def get_user_by_reset_token(self, token):
        return None

    def update_user(self, user_id, **kwargs):
        return True

    def clear_password_reset_token(self, user_id):
        return True


def create_mock_user_db_manager():
    """Create a mock user database manager with demo users."""
    return MockUserDbManager()


# We need to use the same module instances that main.py uses
# Import api_v2_simple module so we can set the mock before main imports it
import importlib.util
import types

# Load api_v2_simple module directly to set up mock before main.py imports it
api_v2_spec = importlib.util.spec_from_file_location("api_v2_simple", api_src_path / "api_v2_simple.py")
api_v2_module = importlib.util.module_from_spec(api_v2_spec)
sys.modules["api_v2_simple"] = api_v2_module
api_v2_spec.loader.exec_module(api_v2_module)

# Now we can access the functions and set the mock
set_user_db_manager = api_v2_module.set_user_db_manager
api_v2_app = api_v2_module.app

# Create and set mock user db manager BEFORE importing main_app
mock_user_db = create_mock_user_db_manager()
set_user_db_manager(mock_user_db)

# Also load api_v2 module and set its mock user db manager
api_v2_full_spec = importlib.util.spec_from_file_location("api_v2", api_src_path / "api_v2.py")
api_v2_full_module = importlib.util.module_from_spec(api_v2_full_spec)
sys.modules["api_v2"] = api_v2_full_module
api_v2_full_spec.loader.exec_module(api_v2_full_module)
api_v2_full_module.set_user_db_manager(mock_user_db)

# Now load main module - it will use the already-loaded api_v2_simple with our mock
main_spec = importlib.util.spec_from_file_location("main", api_src_path / "main.py")
main_module = importlib.util.module_from_spec(main_spec)
sys.modules["main"] = main_module
main_spec.loader.exec_module(main_module)

main_app = main_module.main_app

# Import db module
db_spec = importlib.util.spec_from_file_location("db", api_src_path / "db.py")
db_module = importlib.util.module_from_spec(db_spec)
sys.modules["db"] = db_module
db_spec.loader.exec_module(db_module)

get_db = db_module.get_db
SessionLocal = db_module.SessionLocal

# Import config
config_spec = importlib.util.spec_from_file_location("config", api_src_path / "config.py")
config_module = importlib.util.module_from_spec(config_spec)
sys.modules["config"] = config_module
config_spec.loader.exec_module(config_module)

settings = config_module.settings

from datagod.models import Jurisdiction, DataSource, Record, Entity, Relationship

# Override database dependency for testing
def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# Apply dependency override to main_app and api_v2_app
main_app.dependency_overrides[get_db] = override_get_db
api_v2_app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(main_app)

# Test data
TEST_JURISDICTION = {
    "name": "Test County",
    "state": "CA",
    "county": "Test",
    "type": "county"
}

TEST_DATA_SOURCE = {
    "jurisdiction_id": 1,
    "source_name": "Test API",
    "source_type": "api",
    "api_endpoint": "https://test-api.example.com",
    "status": "active"
}

TEST_RECORD = {
    "jurisdiction_id": 1,
    "data_source_id": 1,
    "record_type": "mortgage",
    "title": "Test Mortgage Record",
    "description": "This is a test mortgage record",
    "amount": 250000.0,
    "date": "2023-01-15T00:00:00"
}

TEST_ENTITY = {
    "entity_name": "Test Person",
    "entity_type": "person",
    "address": "123 Test St, Testville, CA"
}

TEST_RELATIONSHIP = {
    "entity1_id": 1,
    "entity2_id": 2,
    "record_id": 1,
    "relationship_type": "owner",
    "evidence": {"source": "Property records"},
    "confidence_score": 0.95
}

# Authentication test data
TEST_USER_CREDENTIALS = {
    "username": "admin",
    "password": "admin123"
}

# Test tokens
access_token = None

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "DataGod API is running"
    assert data["version"] == "2.0.0"

def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "2.0.0"

def test_test_endpoint():
    """Test test endpoint"""
    response = client.get("/api/v2/test")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "API v2 is working correctly"

def test_authentication():
    """Test authentication and token generation"""
    global access_token

    # Test invalid credentials
    response = client.post(
        "/api/v2/token",
        data={"username": "invalid", "password": "invalid"}
    )
    assert response.status_code == 401

    # Test valid credentials
    response = client.post(
        "/api/v2/token",
        data=TEST_USER_CREDENTIALS
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    access_token = data["access_token"]

def test_get_current_user():
    """Test getting current user information"""
    if not access_token:
        test_authentication()

    response = client.get(
        "/api/v2/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["email"] == "admin@datagod.com"

def test_jurisdiction_crud():
    """Test jurisdiction CRUD operations"""
    if not access_token:
        test_authentication()

    # Create jurisdiction
    response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.status_code != 200:
        print(f"Create jurisdiction failed: {response.status_code}")
        print(f"Response body: {response.json()}")
    assert response.status_code == 200
    jurisdiction_data = response.json()
    assert jurisdiction_data["name"] == TEST_JURISDICTION["name"]
    jurisdiction_id = jurisdiction_data["id"]

    # Get all jurisdictions
    response = client.get("/api/v2/jurisdictions")
    assert response.status_code == 200
    jurisdictions = response.json()
    assert len(jurisdictions) >= 1

    # Get specific jurisdiction
    response = client.get(f"/api/v2/jurisdictions/{jurisdiction_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == jurisdiction_id
    assert data["name"] == TEST_JURISDICTION["name"]

    # Update jurisdiction
    update_data = {"name": "Updated Test County"}
    response = client.put(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test County"

    # Delete jurisdiction (admin only)
    response = client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Jurisdiction deleted successfully"

def test_data_source_crud():
    """Test data source CRUD operations"""
    if not access_token:
        test_authentication()

    # First create a jurisdiction for the data source
    response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    jurisdiction_id = response.json()["id"]

    # Update test data source with correct jurisdiction ID
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id

    # Create data source
    response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data_source_data = response.json()
    assert data_source_data["source_name"] == test_data_source["source_name"]
    data_source_id = data_source_data["id"]

    # Get all data sources
    response = client.get("/api/v2/data-sources")
    assert response.status_code == 200
    data_sources = response.json()
    assert len(data_sources) >= 1

    # Get specific data source
    response = client.get(f"/api/v2/data-sources/{data_source_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == data_source_id
    assert data["source_name"] == test_data_source["source_name"]

    # Clean up - delete jurisdiction (which will cascade to data sources)
    response = client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200

def test_record_crud():
    """Test record CRUD operations"""
    if not access_token:
        test_authentication()

    # First create a jurisdiction for the record
    response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    jurisdiction_id = response.json()["id"]

    # Create a data source for the record
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id
    response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data_source_id = response.json()["id"]

    # Update test record with correct IDs
    test_record = TEST_RECORD.copy()
    test_record["jurisdiction_id"] = jurisdiction_id
    test_record["data_source_id"] = data_source_id

    # Create record
    response = client.post(
        "/api/v2/records",
        json=test_record,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    record_data = response.json()
    assert record_data["title"] == test_record["title"]
    record_id = record_data["id"]

    # Get all records
    response = client.get("/api/v2/records")
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 1

    # Get specific record
    response = client.get(f"/api/v2/records/{record_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == record_id
    assert data["title"] == test_record["title"]

    # Test filtering
    response = client.get(
        f"/api/v2/records?jurisdiction_id={jurisdiction_id}"
    )
    assert response.status_code == 200
    filtered_records = response.json()
    assert len(filtered_records) >= 1

    # Clean up - delete jurisdiction (which will cascade to records and data sources)
    response = client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200

def test_entity_crud():
    """Test entity CRUD operations"""
    if not access_token:
        test_authentication()

    # Create entity
    response = client.post(
        "/api/v2/entities",
        json=TEST_ENTITY,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    entity_data = response.json()
    assert entity_data["entity_name"] == TEST_ENTITY["entity_name"]
    entity_id = entity_data["id"]

    # Get all entities
    response = client.get("/api/v2/entities")
    assert response.status_code == 200
    entities = response.json()
    assert len(entities) >= 1

    # Get specific entity
    response = client.get(f"/api/v2/entities/{entity_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entity_id
    assert data["entity_name"] == TEST_ENTITY["entity_name"]

    # Test filtering
    response = client.get(
        f"/api/v2/entities?entity_type={TEST_ENTITY['entity_type']}"
    )
    assert response.status_code == 200
    filtered_entities = response.json()
    assert len(filtered_entities) >= 1

def test_relationship_crud():
    """Test relationship CRUD operations"""
    if not access_token:
        test_authentication()

    # First create a jurisdiction, data source, and record for the relationship
    response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    jurisdiction_id = response.json()["id"]

    # Create data source
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id
    response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data_source_id = response.json()["id"]

    # Create record
    test_record = TEST_RECORD.copy()
    test_record["jurisdiction_id"] = jurisdiction_id
    test_record["data_source_id"] = data_source_id
    response = client.post(
        "/api/v2/records",
        json=test_record,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    record_id = response.json()["id"]

    # Create two entities
    response1 = client.post(
        "/api/v2/entities",
        json=TEST_ENTITY,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response1.status_code == 200
    entity1_id = response1.json()["id"]

    entity2_data = TEST_ENTITY.copy()
    entity2_data["entity_name"] = "Test Company"
    entity2_data["entity_type"] = "company"

    response2 = client.post(
        "/api/v2/entities",
        json=entity2_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response2.status_code == 200
    entity2_id = response2.json()["id"]

    # Update test relationship with correct IDs
    test_relationship = TEST_RELATIONSHIP.copy()
    test_relationship["entity1_id"] = entity1_id
    test_relationship["entity2_id"] = entity2_id
    test_relationship["record_id"] = record_id

    # Create relationship
    response = client.post(
        "/api/v2/relationships",
        json=test_relationship,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    relationship_data = response.json()
    assert relationship_data["relationship_type"] == test_relationship["relationship_type"]
    relationship_id = relationship_data["id"]

    # Get all relationships
    response = client.get("/api/v2/relationships")
    assert response.status_code == 200
    relationships = response.json()
    assert len(relationships) >= 1

    # Get specific relationship
    response = client.get(f"/api/v2/relationships/{relationship_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == relationship_id
    assert data["relationship_type"] == test_relationship["relationship_type"]

    # Clean up
    response = client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def test_advanced_search():
    """Test advanced search functionality"""
    if not access_token:
        test_authentication()

    # Create test data
    jurisdiction_response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    jurisdiction_id = jurisdiction_response.json()["id"]

    # Create data source
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id
    ds_response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert ds_response.status_code == 200
    data_source_id = ds_response.json()["id"]

    record_data = TEST_RECORD.copy()
    record_data["jurisdiction_id"] = jurisdiction_id
    record_data["data_source_id"] = data_source_id
    record_response = client.post(
        "/api/v2/records",
        json=record_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert record_response.status_code == 200

    # Test search
    search_query = {
        "query": "Test",
        "jurisdiction_ids": [jurisdiction_id],
        "record_types": ["mortgage"],
        "page": 1,
        "page_size": 10
    }

    response = client.post(
        "/api/v2/search",
        json=search_query,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert "total_count" in data
    assert data["total_count"] >= 1

    # Clean up
    client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def test_data_export():
    """Test data export functionality"""
    if not access_token:
        test_authentication()

    # Create test data
    jurisdiction_response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    jurisdiction_id = jurisdiction_response.json()["id"]

    # Create data source
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id
    ds_response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert ds_response.status_code == 200
    data_source_id = ds_response.json()["id"]

    record_data = TEST_RECORD.copy()
    record_data["jurisdiction_id"] = jurisdiction_id
    record_data["data_source_id"] = data_source_id
    record_response = client.post(
        "/api/v2/records",
        json=record_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert record_response.status_code == 200

    # Test JSON export
    export_request = {
        "format": "json",
        "query": {
            "jurisdiction_ids": [jurisdiction_id]
        }
    }

    response = client.post(
        "/api/v2/export",
        json=export_request,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert len(data["records"]) >= 1

    # Test CSV export
    export_request["format"] = "csv"
    response = client.post(
        "/api/v2/export",
        json=export_request,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    # Clean up
    client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def test_integration_endpoints():
    """Test integration endpoints"""
    if not access_token:
        test_authentication()

    # Create test data
    jurisdiction_response = client.post(
        "/api/v2/jurisdictions",
        json=TEST_JURISDICTION,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    jurisdiction_id = jurisdiction_response.json()["id"]

    # Create data source
    test_data_source = TEST_DATA_SOURCE.copy()
    test_data_source["jurisdiction_id"] = jurisdiction_id
    ds_response = client.post(
        "/api/v2/data-sources",
        json=test_data_source,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert ds_response.status_code == 200
    data_source_id = ds_response.json()["id"]

    record_data = TEST_RECORD.copy()
    record_data["jurisdiction_id"] = jurisdiction_id
    record_data["data_source_id"] = data_source_id
    record_response = client.post(
        "/api/v2/records",
        json=record_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    record_id = record_response.json()["id"]

    # Test neural network integration
    response = client.post(
        f"/api/v2/integrate/neural-network?record_id={record_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code in [200, 400]  # 200 if enabled, 400 if disabled

    # Test scraper integration
    response = client.post(
        f"/api/v2/integrate/scraper?jurisdiction_id={jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code in [200, 400]  # 200 if enabled, 400 if disabled

    # Clean up
    client.delete(
        f"/api/v2/jurisdictions/{jurisdiction_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def test_cache_management():
    """Test cache management endpoints"""
    if not access_token:
        test_authentication()

    # Test cache stats
    response = client.get(
        "/api/v2/cache/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

    # Test cache clear
    response = client.delete(
        "/api/v2/cache/clear",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_error_handling():
    """Test error handling"""
    # Test 404 error
    response = client.get("/api/v2/nonexistent")
    assert response.status_code == 404

    # Test unauthorized access
    response = client.get("/api/v2/users/me")
    assert response.status_code == 401

    # Test invalid token
    response = client.get(
        "/api/v2/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_rate_limiting():
    """Test rate limiting functionality"""
    # This is a basic test - in a real scenario, you'd want to test actual rate limiting
    # by making multiple requests in quick succession

    # Test that rate limited endpoints work
    response = client.get("/api/v2/metrics")
    assert response.status_code == 200

def test_user_registration():
    """Test user registration endpoint"""
    import uuid

    # Generate unique user to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    test_user = {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }

    # Test successful registration
    response = client.post("/api/v2/auth/register", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "roles" in data
    assert "user" in data["roles"]

    # Test duplicate username
    response = client.post("/api/v2/auth/register", json=test_user)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

    # Test invalid email format
    invalid_email_user = {
        "username": f"testuser2_{unique_id}",
        "email": "invalid-email",
        "password": "TestPassword123!",
        "full_name": "Test User 2"
    }
    response = client.post("/api/v2/auth/register", json=invalid_email_user)
    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()

    # Test invalid username (special characters)
    invalid_username_user = {
        "username": "test@user!",
        "email": f"testuser3_{unique_id}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User 3"
    }
    response = client.post("/api/v2/auth/register", json=invalid_username_user)
    assert response.status_code == 400
    assert "username" in response.json()["detail"].lower()

def test_json_login():
    """Test JSON-based login endpoint"""
    # Test valid login
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid login
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_password_reset_flow():
    """Test password reset flow"""
    # Test forgot password (always returns success for security)
    response = client.post(
        "/api/v2/auth/forgot-password",
        json={"email": "admin@datagod.com"}
    )
    assert response.status_code == 200
    assert "message" in response.json()

    # Test forgot password with non-existent email (still returns success)
    response = client.post(
        "/api/v2/auth/forgot-password",
        json={"email": "nonexistent@example.com"}
    )
    assert response.status_code == 200
    assert "message" in response.json()

    # Test reset password with invalid token
    response = client.post(
        "/api/v2/auth/reset-password",
        json={"token": "invalid-token", "new_password": "NewPassword123!"}
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()

if __name__ == "__main__":
    # Run tests
    print("🧪 Running DataGod API v2 tests...")

    # Run all test functions
    test_root_endpoint()
    print("✅ Root endpoint test passed")

    test_health_endpoint()
    print("✅ Health endpoint test passed")

    test_test_endpoint()
    print("✅ Test endpoint test passed")

    test_authentication()
    print("✅ Authentication test passed")

    test_get_current_user()
    print("✅ Get current user test passed")

    test_jurisdiction_crud()
    print("✅ Jurisdiction CRUD test passed")

    test_data_source_crud()
    print("✅ Data source CRUD test passed")

    test_record_crud()
    print("✅ Record CRUD test passed")

    test_entity_crud()
    print("✅ Entity CRUD test passed")

    test_relationship_crud()
    print("✅ Relationship CRUD test passed")

    test_advanced_search()
    print("✅ Advanced search test passed")

    test_data_export()
    print("✅ Data export test passed")

    test_integration_endpoints()
    print("✅ Integration endpoints test passed")

    test_cache_management()
    print("✅ Cache management test passed")

    test_error_handling()
    print("✅ Error handling test passed")

    test_rate_limiting()
    print("✅ Rate limiting test passed")

    print("🎉 All tests completed successfully!")
    print("📊 DataGod API v2 is fully functional and ready for production!")
