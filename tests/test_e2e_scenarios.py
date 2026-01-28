
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from unittest.mock import patch

from api.src.api_v2 import app, get_db
from datagod.models import User
from datagod.schemas.auth import UserCreate, Token
from datagod.schemas.core import (
    JurisdictionCreate, JurisdictionResponse,
    DataSourceCreate, DataSourceResponse,
    RecordCreate, RecordResponse,
    ScraperRunResponse
)

# --- Fixtures ---

@pytest.fixture
def client(db_session):
    """Create a TestClient that uses the test database session"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_db_manager(db_session):
    """Mock UserDBManager that uses the SQLAlchemy session"""
    class MockUserDB:
        def get_user_for_auth(self, username):
            # Query SQLAlchemy session
            from datagod.models import User
            user = db_session.query(User).filter(User.username == username).first()
            if user:
                # Convert to dict format expected by auth logic
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "roles": user.roles,
                    "disabled": user.disabled,
                    "locked_until": user.locked_until
                }
            return None

        def check_user_locked(self, username):
            return False

        def record_login(self, username, success):
            pass
            
        def get_user_by_username(self, username):
            from datagod.models import User
            user = db_session.query(User).filter(User.username == username).first()
            if user:
                 return user.to_dict()
            return None

        def get_user_by_email(self, email):
            from datagod.models import User
            user = db_session.query(User).filter(User.email == email).first()
            if user:
                 return user.to_dict()
            return None

        def create_user(self, username, email, hashed_password, full_name=None, roles=None, disabled=False, email_verified=False):
            from datagod.models import User
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                roles=roles or ["user"],
                disabled=disabled,
                email_verified=email_verified
            )
            db_session.add(user)
            db_session.commit()
            return user.id

    mock_db = MockUserDB()
    with patch("api.src.api_v2.user_db_manager", mock_db):
        yield mock_db

@pytest.fixture
def admin_token(client, db_session, mock_user_db_manager):
    """Create an admin user and return a valid access token"""
    from datagod.models import User
    from api.src.api_v2 import get_password_hash
    
    # Check if admin already exists (fixture might run multiple times or shared DB)
    existing = db_session.query(User).filter_by(username="admin").first()
    if not existing:
        admin_data = {
            "email": "admin@datagod.com",
            "username": "admin",
            "hashed_password": get_password_hash("admin123"),
            "roles": ["admin"],
            "disabled": False,
            "email_verified": True
        }
        user = User(**admin_data)
        db_session.add(user)
        db_session.commit()
    
    # Login to get token
    response = client.post("/token", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture
def regular_token(client, db_session, mock_user_db_manager):
    """Create a regular user and return a valid access token"""
    from datagod.models import User
    from api.src.api_v2 import get_password_hash
    
    existing = db_session.query(User).filter_by(username="user").first()
    if not existing:
        user_data = {
            "email": "user@datagod.com",
            "username": "user",
            "hashed_password": get_password_hash("user123"),
            "roles": ["user"],
            "disabled": False,
            "email_verified": True
        }
        user = User(**user_data)
        db_session.add(user)
        db_session.commit()
    
    # Login to get token
    response = client.post("/token", data={"username": "user", "password": "user123"})
    assert response.status_code == 200
    return response.json()["access_token"]

# --- E2E User Flow Scenarios ---

class TestUserFlow:
    """End-to-End User Workflows"""

    def test_user_lifecycle(self, client, db_session, mock_user_db_manager):
        """
        Test the full lifecycle of a user:
        1. Register
        2. Login
        3. Search for records (empty initially)
        4. Request export
        """
        # 1. Register
        reg_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "full_name": "New User"
        }
        res = client.post("/auth/register", json=reg_data)
        assert res.status_code == 201, f"Registration failed: {res.text}"
        
        # Verify user is in DB but not active/verified (depending on settings, but assuming default flow)
        # For this test, manually activate if needed, or check if response implies success
        
        # 2. Login
        login_data = {"username": "newuser", "password": "password123"}
        res = client.post("/token", data=login_data)
        
        if res.status_code == 400:
            # Maybe inactive? Manually activate for test sake
            user = db_session.query(User).filter_by(email="newuser@example.com").first()
            if user:
                user.disabled = False
                user.email_verified = True
                db_session.commit()
            
            # Retry login
            res = client.post("/token", data=login_data)
        
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Search Records (should be empty initially)
        res = client.post("/search", json={"query": "test"}, headers=headers)
        assert res.status_code == 200, f"Search failed: {res.text}"
        data = res.json()
        assert data["total_count"] == 0
        
        # 4. Request Export
        export_req = {
            "format": "csv",
            "query": {"query": "test"}
        }
        res = client.post("/export", json=export_req, headers=headers)
        # Note: Depending on implementation, this might return a stream or a job ID.
        # api_v2.py endpoint: @app.post("/export") -> returns FileResponse or similar
        # If it returns a file, status should be 200.
        assert res.status_code in [200, 202], f"Export failed: {res.text}"


class TestAdminFlow:
    """End-to-End Admin Workflows"""

    def test_admin_jurisdiction_management(self, client, admin_token, db_session):
        """
        Test Admin workflow:
        1. Login (handled by fixture)
        2. Create Jurisdiction
        3. Create Data Source
        4. Trigger Scraper (mocked likely, as we won't run real scraper here)
        5. Verify Scraper Run Log
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Create Jurisdiction
        jur_data = {
            "name": "E2E Test County",
            "state": "TX",
            "county": "Test",
            "type": "county",
            "api_available": True,
            "scraper_needed": True
        }
        res = client.post("/jurisdictions/", json=jur_data, headers=headers)
        assert res.status_code == 200, f"Create Jurisdiction failed: {res.text}"
        jurisdiction = res.json()
        jur_id = jurisdiction["id"]
        
        # 3. Create Data Source
        ds_data = {
            "jurisdiction_id": jur_id,
            "source_name": "Official Records",
            "source_type": "api",
            "url": "http://example.com"
        }
        res = client.post("/data-sources/", json=ds_data, headers=headers)
        assert res.status_code == 200, f"Create DataSource failed: {res.text}"
        ds_id = res.json()["id"]
        
        # 4. Create dummy records to simulate 'scraping' result
        # Since we can't easily run a background scraper task in this sync test without external worker
        # We will simulate the effect by manually adding records and a scraper run log
        
        # Simulate Scraper Run Log creation (Admin API usually has read-only for logs, 
        # but scrapers use internal DB access. We'll use the DB session to insert a run log)
        from datagod.models import ScraperRun
        run = ScraperRun(
            jurisdiction_id=jur_id,
            scraper_module="TestScraper",
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            status="success",
            records_found=10,
            records_new=10
        )
        db_session.add(run)
        db_session.commit()
        
        # 5. Verify Scraper Run Logs via Admin API
        res = client.get("/admin/scrapers/runs", headers=headers)
        assert res.status_code == 200
        runs = res.json()
        assert len(runs) > 0
        assert runs[0]["jurisdiction_id"] == jur_id
        assert runs[0]["status"] == "success"
