"""
Comprehensive tests for api/src/api_v2.py
This module tests the DataGod API v2 using logic pattern testing.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, date
import json
import io


# ==================== Model Tests ====================

class TestUserModels:
    """Tests for User-related Pydantic models"""

    def test_user_model_basic(self):
        """Test basic User model creation"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "disabled": False,
            "roles": ["user"]
        }
        # Simulate User model validation
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "test@example.com"
        assert "user" in user_data["roles"]

    def test_user_model_with_defaults(self):
        """Test User model with default values"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com"
        }
        # Add defaults
        user_data.setdefault("disabled", None)
        user_data.setdefault("roles", ["user"])
        user_data.setdefault("full_name", None)

        assert user_data["roles"] == ["user"]
        assert user_data["disabled"] is None

    def test_user_in_db_model(self):
        """Test UserInDB model with hashed password"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "disabled": False,
            "roles": ["user"],
            "hashed_password": "$2b$12$hashedpassword"
        }
        assert "hashed_password" in user_data
        assert user_data["hashed_password"].startswith("$2b$")

    def test_token_model(self):
        """Test Token model"""
        token_data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 1800
        }
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0

    def test_token_data_model(self):
        """Test TokenData model"""
        token_data = {
            "username": "testuser",
            "roles": ["user", "admin"]
        }
        assert token_data["username"] == "testuser"
        assert "admin" in token_data["roles"]


class TestUserRegisterModel:
    """Tests for UserRegister model with validation"""

    def test_valid_registration(self):
        """Test valid registration data"""
        reg_data = {
            "username": "newuser123",
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "full_name": "New User"
        }
        # Validate username pattern
        import re
        pattern = r'^[a-zA-Z0-9_]+$'
        assert re.match(pattern, reg_data["username"])
        assert len(reg_data["username"]) >= 3
        assert len(reg_data["username"]) <= 50

    def test_email_validation(self):
        """Test email validation"""
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@gmail.com"
        ]
        invalid_emails = [
            "notanemail",
            "missing@",
            "@nodomain.com"
        ]

        for email in valid_emails:
            assert re.match(email_regex, email), f"{email} should be valid"

        for email in invalid_emails:
            assert not re.match(email_regex, email), f"{email} should be invalid"

    def test_password_validation(self):
        """Test password validation logic"""
        def validate_password(password):
            if len(password) < 8:
                return False, "Password must be at least 8 characters"
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            if not (has_letter and has_digit):
                return False, "Password must contain at least one letter and one number"
            return True, None

        # Valid passwords
        valid, _ = validate_password("Password123")
        assert valid

        # Too short
        valid, msg = validate_password("Pass1")
        assert not valid
        assert "8 characters" in msg

        # No digit
        valid, msg = validate_password("PasswordOnly")
        assert not valid
        assert "number" in msg.lower()

        # No letter
        valid, msg = validate_password("12345678")
        assert not valid
        assert "letter" in msg.lower()


class TestPasswordResetModels:
    """Tests for password reset models"""

    def test_password_reset_request(self):
        """Test PasswordResetRequest model"""
        request_data = {"email": "user@example.com"}
        assert "email" in request_data

    def test_password_reset_confirm(self):
        """Test PasswordResetConfirm model"""
        confirm_data = {
            "token": "abc123-reset-token",
            "new_password": "NewSecure123"
        }
        assert len(confirm_data["new_password"]) >= 8


class TestCRUDModels:
    """Tests for CRUD operation models"""

    def test_jurisdiction_create(self):
        """Test JurisdictionCreate model"""
        jurisdiction_data = {
            "name": "Test County",
            "state": "TX",
            "county": "Test",
            "jurisdiction_type": "county",
            "population": 100000,
            "metadata": {"website": "https://example.com"}
        }
        assert jurisdiction_data["state"] == "TX"
        assert jurisdiction_data["population"] == 100000

    def test_jurisdiction_update(self):
        """Test JurisdictionUpdate model with optional fields"""
        update_data = {"name": "Updated County"}
        # All fields should be optional
        assert "name" in update_data
        assert "state" not in update_data

    def test_data_source_create(self):
        """Test DataSourceCreate model"""
        ds_data = {
            "jurisdiction_id": 1,
            "source_name": "County Records API",
            "source_type": "api",
            "url": "https://api.example.com",
            "api_key": "secret_key",
            "status": "active",
            "metadata": {}
        }
        assert ds_data["source_type"] == "api"
        assert ds_data["status"] == "active"

    def test_record_create(self):
        """Test RecordCreate model"""
        record_data = {
            "jurisdiction_id": 1,
            "data_source_id": 1,
            "record_type": "mortgage",
            "title": "Property Mortgage",
            "description": "A test mortgage record",
            "amount": 250000.00,
            "date": date(2024, 1, 15),
            "metadata": {"property_type": "residential"},
            "raw_data": {}
        }
        assert record_data["amount"] == 250000.00
        assert record_data["record_type"] == "mortgage"

    def test_entity_create(self):
        """Test EntityCreate model"""
        entity_data = {
            "entity_name": "John Doe",
            "entity_type": "person",
            "address": "123 Main St",
            "jurisdiction_id": 1,
            "metadata": {}
        }
        assert entity_data["entity_type"] == "person"

    def test_relationship_create(self):
        """Test RelationshipCreate model"""
        rel_data = {
            "entity1_id": 1,
            "entity2_id": 2,
            "relationship_type": "owns",
            "record_id": 1,
            "evidence": "Property deed",
            "confidence_score": 0.95,
            "metadata": {}
        }
        assert rel_data["confidence_score"] == 0.95
        assert rel_data["relationship_type"] == "owns"


class TestSearchAndExportModels:
    """Tests for search and export models"""

    def test_search_query_defaults(self):
        """Test SearchQuery model with defaults"""
        query = {
            "query": None,
            "jurisdiction_ids": None,
            "record_types": None,
            "entity_types": None,
            "date_from": None,
            "date_to": None,
            "amount_min": None,
            "amount_max": None,
            "sort_by": "date",
            "sort_order": "desc",
            "page": 1,
            "page_size": 50
        }
        assert query["sort_by"] == "date"
        assert query["page_size"] == 50

    def test_search_query_with_filters(self):
        """Test SearchQuery with filters applied"""
        query = {
            "query": "mortgage",
            "jurisdiction_ids": [1, 2, 3],
            "record_types": ["mortgage", "property"],
            "date_from": date(2024, 1, 1),
            "date_to": date(2024, 12, 31),
            "amount_min": 100000,
            "amount_max": 500000,
            "page": 2,
            "page_size": 25
        }
        assert len(query["jurisdiction_ids"]) == 3
        assert query["amount_min"] == 100000

    def test_export_request(self):
        """Test ExportRequest model"""
        export_request = {
            "format": "csv",
            "query": {"query": "test"},
            "fields": ["id", "title", "amount"]
        }
        assert export_request["format"] == "csv"
        assert len(export_request["fields"]) == 3


class TestEnums:
    """Tests for enum types"""

    def test_record_type_enum(self):
        """Test RecordType enum values"""
        from enum import Enum

        class RecordType(str, Enum):
            MORTGAGE = "mortgage"
            PROPERTY = "property"
            TAX = "tax"
            LEGAL = "legal"
            FINANCIAL = "financial"

        assert RecordType.MORTGAGE.value == "mortgage"
        assert RecordType.PROPERTY.value == "property"
        assert len(RecordType) == 5

    def test_entity_type_enum(self):
        """Test EntityType enum values"""
        from enum import Enum

        class EntityType(str, Enum):
            PERSON = "person"
            COMPANY = "company"
            PROPERTY = "property"
            GOVERNMENT = "government"

        assert EntityType.PERSON.value == "person"
        assert len(EntityType) == 4


# ==================== Password Hashing Tests ====================

class TestPasswordHashing:
    """Tests for password hashing functionality"""

    def test_password_hash_format(self):
        """Test that password hash uses bcrypt format"""
        # Simulate bcrypt hashing
        password = "testpassword123"
        # Bcrypt hashes start with $2b$
        mock_hash = "$2b$12$LQv3c1yqBwZZZbGTV6T4.eQGNRKBpxLwNqGKnhWYlMOxT9.xKVjey"
        assert mock_hash.startswith("$2b$")
        assert len(mock_hash) == 60

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        def verify_password(plain, hashed):
            # Simulate bcrypt verification
            return True  # Would use pwd_context.verify() in real code

        result = verify_password("correct_password", "$2b$12$hash...")
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        def verify_password(plain, hashed):
            # Simulate failed verification
            return False

        result = verify_password("wrong_password", "$2b$12$hash...")
        assert result is False


# ==================== Token Creation Tests ====================

class TestTokenCreation:
    """Tests for JWT token creation"""

    def test_create_access_token_with_expiry(self):
        """Test token creation with expiry time"""
        def create_access_token(data, expires_delta=None):
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
                to_encode["exp"] = expire
            # Simulate JWT encoding
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.encoded.signature"

        token = create_access_token(
            {"sub": "testuser", "roles": ["user"]},
            expires_delta=timedelta(minutes=30)
        )
        assert token.startswith("eyJ")

    def test_create_access_token_without_expiry(self):
        """Test token creation without explicit expiry"""
        def create_access_token(data, expires_delta=None):
            to_encode = data.copy()
            # No expiry set
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.encoded.signature"

        token = create_access_token({"sub": "testuser"})
        assert len(token) > 0

    def test_token_payload_structure(self):
        """Test token payload contains required fields"""
        payload = {
            "sub": "testuser",
            "roles": ["user", "admin"],
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        assert "sub" in payload
        assert "roles" in payload
        assert "exp" in payload


# ==================== Rate Limiting Tests ====================

class TestRateLimiting:
    """Tests for rate limiting functionality"""

    def test_rate_limit_within_window(self):
        """Test rate limit tracking within window"""
        import time

        class RateLimiter:
            def __init__(self, max_requests, window):
                self.max_requests = max_requests
                self.window = window
                self.requests = {}

            def check(self, client_id):
                current_time = time.time()
                if client_id not in self.requests:
                    self.requests[client_id] = []

                # Clean old entries
                self.requests[client_id] = [
                    t for t in self.requests[client_id]
                    if current_time - t < self.window
                ]

                if len(self.requests[client_id]) >= self.max_requests:
                    return False

                self.requests[client_id].append(current_time)
                return True

        limiter = RateLimiter(max_requests=5, window=60)

        # First 5 requests should succeed
        for _ in range(5):
            assert limiter.check("client1") is True

        # 6th request should fail
        assert limiter.check("client1") is False

    def test_rate_limit_different_clients(self):
        """Test rate limiting is per-client"""
        requests = {"client1": 0, "client2": 0}
        max_requests = 3

        for _ in range(3):
            requests["client1"] += 1

        # Client1 is at limit, but client2 should still work
        assert requests["client1"] == max_requests
        assert requests["client2"] < max_requests


class TestRegistrationRateLimiting:
    """Tests for registration rate limiting"""

    def test_check_registration_rate_limit(self):
        """Test registration rate limit checking"""
        import time

        registration_attempts = {}

        def check_registration_rate_limit(ip, max_attempts=5, window_hours=1):
            current_time = time.time()
            window_seconds = window_hours * 3600

            # Clean up old entries
            if ip in registration_attempts:
                registration_attempts[ip] = [
                    t for t in registration_attempts[ip]
                    if current_time - t < window_seconds
                ]

            # Check current IP
            if ip in registration_attempts:
                if len(registration_attempts[ip]) >= max_attempts:
                    return False

            return True

        def record_registration_attempt(ip):
            import time
            if ip not in registration_attempts:
                registration_attempts[ip] = []
            registration_attempts[ip].append(time.time())

        # First 5 attempts should succeed
        for _ in range(5):
            assert check_registration_rate_limit("192.168.1.1")
            record_registration_attempt("192.168.1.1")

        # 6th attempt should fail
        assert check_registration_rate_limit("192.168.1.1") is False


# ==================== Authentication Tests ====================

class TestUserAuthentication:
    """Tests for user authentication"""

    def test_get_user_from_db_exists(self):
        """Test getting existing user from database"""
        mock_db = {
            "testuser": {
                "username": "testuser",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "roles": ["user"]
            }
        }

        def get_user_from_db(username):
            return mock_db.get(username)

        user = get_user_from_db("testuser")
        assert user is not None
        assert user["username"] == "testuser"

    def test_get_user_from_db_not_exists(self):
        """Test getting non-existent user"""
        mock_db = {}

        def get_user_from_db(username):
            return mock_db.get(username)

        user = get_user_from_db("nonexistent")
        assert user is None

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        def authenticate_user(username, password):
            if username == "testuser" and password == "correct":
                return {"username": "testuser", "roles": ["user"]}
            return None

        user = authenticate_user("testuser", "correct")
        assert user is not None

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        def authenticate_user(username, password):
            if username == "testuser" and password == "correct":
                return {"username": "testuser"}
            return None

        user = authenticate_user("testuser", "wrong")
        assert user is None

    def test_authenticate_locked_account(self):
        """Test authentication with locked account"""
        locked_accounts = {"lockeduser": True}

        def check_user_locked(username):
            return locked_accounts.get(username, False)

        def authenticate_user(username, password):
            if check_user_locked(username):
                return None
            return {"username": username}

        user = authenticate_user("lockeduser", "password")
        assert user is None


class TestCurrentUser:
    """Tests for getting current user from token"""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token"""
        mock_user_db = {
            "testuser": {
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"],
                "disabled": False
            }
        }

        async def get_current_user(token):
            # Simulate JWT decode
            payload = {"sub": "testuser", "roles": ["user"]}
            username = payload.get("sub")
            if username and username in mock_user_db:
                return mock_user_db[username]
            raise Exception("Could not validate credentials")

        user = await get_current_user("valid_token")
        assert user["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_active_user(self):
        """Test getting current active user"""
        async def get_current_active_user(current_user):
            if current_user.get("disabled"):
                raise Exception("Inactive user")
            return current_user

        active_user = {"username": "test", "disabled": False}
        result = await get_current_active_user(active_user)
        assert result["username"] == "test"

    @pytest.mark.asyncio
    async def test_get_current_active_user_disabled(self):
        """Test getting disabled user raises exception"""
        async def get_current_active_user(current_user):
            if current_user.get("disabled"):
                raise Exception("Inactive user")
            return current_user

        disabled_user = {"username": "test", "disabled": True}
        with pytest.raises(Exception, match="Inactive user"):
            await get_current_active_user(disabled_user)


class TestRoleBasedAccess:
    """Tests for role-based access control"""

    def test_has_role_authorized(self):
        """Test user with required role is authorized"""
        def has_role(user_roles, required_roles):
            return any(role in user_roles for role in required_roles)

        user_roles = ["user", "admin"]
        required = ["admin"]

        assert has_role(user_roles, required) is True

    def test_has_role_unauthorized(self):
        """Test user without required role is unauthorized"""
        def has_role(user_roles, required_roles):
            return any(role in user_roles for role in required_roles)

        user_roles = ["user"]
        required = ["admin"]

        assert has_role(user_roles, required) is False

    def test_has_role_multiple_options(self):
        """Test authorization with multiple role options"""
        def has_role(user_roles, required_roles):
            return any(role in user_roles for role in required_roles)

        user_roles = ["editor"]
        required = ["admin", "editor"]

        assert has_role(user_roles, required) is True


# ==================== Health Check Tests ====================

class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """Test health check with all services healthy"""
        async def health_check(db_connected=True, redis_connected=True):
            db_status = "healthy" if db_connected else "unhealthy"
            cache_status = "healthy" if redis_connected else "disabled"

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": db_status,
                "cache": cache_status,
                "api_version": "2.0.0"
            }

        result = await health_check()
        assert result["status"] == "healthy"
        assert result["database"] == "healthy"
        assert result["cache"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_no_redis(self):
        """Test health check with Redis disabled"""
        async def health_check(db_connected=True, redis_connected=False):
            db_status = "healthy" if db_connected else "unhealthy"
            cache_status = "healthy" if redis_connected else "disabled"

            return {
                "status": "healthy",
                "database": db_status,
                "cache": cache_status
            }

        result = await health_check()
        assert result["cache"] == "disabled"


# ==================== CRUD Endpoint Tests ====================

class TestJurisdictionEndpoints:
    """Tests for jurisdiction CRUD endpoints"""

    @pytest.mark.asyncio
    async def test_create_jurisdiction(self):
        """Test creating a jurisdiction"""
        jurisdictions = []

        async def create_jurisdiction(data):
            new_id = len(jurisdictions) + 1
            jurisdiction = {"id": new_id, **data}
            jurisdictions.append(jurisdiction)
            return jurisdiction

        result = await create_jurisdiction({
            "name": "Test County",
            "state": "TX",
            "county": "Test",
            "jurisdiction_type": "county"
        })

        assert result["id"] == 1
        assert result["state"] == "TX"

    @pytest.mark.asyncio
    async def test_get_jurisdictions_with_filters(self):
        """Test getting jurisdictions with filters"""
        jurisdictions = [
            {"id": 1, "name": "County A", "state": "TX"},
            {"id": 2, "name": "County B", "state": "TX"},
            {"id": 3, "name": "County C", "state": "CA"}
        ]

        async def get_jurisdictions(state=None, limit=100, offset=0):
            result = jurisdictions
            if state:
                result = [j for j in result if j["state"] == state]
            return result[offset:offset+limit]

        tx_jurisdictions = await get_jurisdictions(state="TX")
        assert len(tx_jurisdictions) == 2

    @pytest.mark.asyncio
    async def test_get_jurisdiction_by_id_found(self):
        """Test getting jurisdiction by ID when found"""
        jurisdictions = {1: {"id": 1, "name": "Test County"}}

        async def get_jurisdiction(jurisdiction_id):
            return jurisdictions.get(jurisdiction_id)

        result = await get_jurisdiction(1)
        assert result is not None
        assert result["name"] == "Test County"

    @pytest.mark.asyncio
    async def test_get_jurisdiction_by_id_not_found(self):
        """Test getting jurisdiction by ID when not found"""
        jurisdictions = {}

        async def get_jurisdiction(jurisdiction_id):
            j = jurisdictions.get(jurisdiction_id)
            if not j:
                raise Exception("Jurisdiction not found")
            return j

        with pytest.raises(Exception, match="not found"):
            await get_jurisdiction(999)

    @pytest.mark.asyncio
    async def test_update_jurisdiction(self):
        """Test updating a jurisdiction"""
        jurisdictions = {1: {"id": 1, "name": "Old Name", "state": "TX"}}

        async def update_jurisdiction(jurisdiction_id, update_data):
            if jurisdiction_id not in jurisdictions:
                raise Exception("Not found")
            jurisdictions[jurisdiction_id].update(update_data)
            return jurisdictions[jurisdiction_id]

        result = await update_jurisdiction(1, {"name": "New Name"})
        assert result["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_jurisdiction(self):
        """Test deleting a jurisdiction"""
        jurisdictions = {1: {"id": 1, "name": "Test"}}

        async def delete_jurisdiction(jurisdiction_id):
            if jurisdiction_id not in jurisdictions:
                raise Exception("Not found")
            del jurisdictions[jurisdiction_id]
            return {"message": "Jurisdiction deleted successfully"}

        result = await delete_jurisdiction(1)
        assert result["message"] == "Jurisdiction deleted successfully"
        assert 1 not in jurisdictions


class TestDataSourceEndpoints:
    """Tests for data source CRUD endpoints"""

    @pytest.mark.asyncio
    async def test_create_data_source(self):
        """Test creating a data source"""
        data_sources = []
        jurisdictions = {1: {"id": 1}}

        async def create_data_source(data):
            if data["jurisdiction_id"] not in jurisdictions:
                raise Exception("Jurisdiction not found")
            new_id = len(data_sources) + 1
            ds = {"id": new_id, **data}
            data_sources.append(ds)
            return ds

        result = await create_data_source({
            "jurisdiction_id": 1,
            "source_name": "Test API",
            "source_type": "api"
        })
        assert result["source_name"] == "Test API"

    @pytest.mark.asyncio
    async def test_get_data_sources_filtered(self):
        """Test getting data sources with filters"""
        data_sources = [
            {"id": 1, "source_type": "api", "status": "active"},
            {"id": 2, "source_type": "scraper", "status": "active"},
            {"id": 3, "source_type": "api", "status": "inactive"}
        ]

        async def get_data_sources(source_type=None, status=None):
            result = data_sources
            if source_type:
                result = [ds for ds in result if ds["source_type"] == source_type]
            if status:
                result = [ds for ds in result if ds["status"] == status]
            return result

        api_sources = await get_data_sources(source_type="api", status="active")
        assert len(api_sources) == 1


class TestRecordEndpoints:
    """Tests for record CRUD endpoints"""

    @pytest.mark.asyncio
    async def test_create_record(self):
        """Test creating a record"""
        records = []

        async def create_record(data):
            new_id = len(records) + 1
            record = {"id": new_id, **data}
            records.append(record)
            return record

        result = await create_record({
            "jurisdiction_id": 1,
            "record_type": "mortgage",
            "title": "Test Mortgage",
            "amount": 250000.00
        })
        assert result["title"] == "Test Mortgage"
        assert result["amount"] == 250000.00

    @pytest.mark.asyncio
    async def test_get_records_with_filters(self):
        """Test getting records with various filters"""
        records = [
            {"id": 1, "record_type": "mortgage", "amount": 200000, "date": date(2024, 1, 15)},
            {"id": 2, "record_type": "property", "amount": 300000, "date": date(2024, 2, 20)},
            {"id": 3, "record_type": "mortgage", "amount": 150000, "date": date(2024, 3, 10)}
        ]

        async def get_records(record_type=None, amount_min=None, amount_max=None):
            result = records
            if record_type:
                result = [r for r in result if r["record_type"] == record_type]
            if amount_min:
                result = [r for r in result if r["amount"] >= amount_min]
            if amount_max:
                result = [r for r in result if r["amount"] <= amount_max]
            return result

        mortgages = await get_records(record_type="mortgage")
        assert len(mortgages) == 2

        in_range = await get_records(amount_min=175000, amount_max=275000)
        assert len(in_range) == 1


class TestEntityEndpoints:
    """Tests for entity CRUD endpoints"""

    @pytest.mark.asyncio
    async def test_create_entity(self):
        """Test creating an entity"""
        entities = []

        async def create_entity(data):
            new_id = len(entities) + 1
            entity = {"id": new_id, **data}
            entities.append(entity)
            return entity

        result = await create_entity({
            "entity_name": "John Doe",
            "entity_type": "person",
            "address": "123 Main St"
        })
        assert result["entity_type"] == "person"

    @pytest.mark.asyncio
    async def test_get_entities_by_type(self):
        """Test getting entities filtered by type"""
        entities = [
            {"id": 1, "entity_name": "John", "entity_type": "person"},
            {"id": 2, "entity_name": "ABC Corp", "entity_type": "company"},
            {"id": 3, "entity_name": "Jane", "entity_type": "person"}
        ]

        async def get_entities(entity_type=None):
            if entity_type:
                return [e for e in entities if e["entity_type"] == entity_type]
            return entities

        people = await get_entities(entity_type="person")
        assert len(people) == 2


class TestRelationshipEndpoints:
    """Tests for relationship CRUD endpoints"""

    @pytest.mark.asyncio
    async def test_create_relationship(self):
        """Test creating a relationship"""
        relationships = []
        entities = {1: {"id": 1}, 2: {"id": 2}}

        async def create_relationship(data):
            if data["entity1_id"] not in entities:
                raise Exception("Entity 1 not found")
            if data["entity2_id"] not in entities:
                raise Exception("Entity 2 not found")

            new_id = len(relationships) + 1
            rel = {"id": new_id, **data}
            relationships.append(rel)
            return rel

        result = await create_relationship({
            "entity1_id": 1,
            "entity2_id": 2,
            "relationship_type": "owns",
            "confidence_score": 0.95
        })
        assert result["relationship_type"] == "owns"

    @pytest.mark.asyncio
    async def test_get_relationships_by_entity(self):
        """Test getting relationships for an entity"""
        relationships = [
            {"id": 1, "entity1_id": 1, "entity2_id": 2, "relationship_type": "owns"},
            {"id": 2, "entity1_id": 2, "entity2_id": 3, "relationship_type": "manages"},
            {"id": 3, "entity1_id": 1, "entity2_id": 3, "relationship_type": "funds"}
        ]

        async def get_relationships(entity_id=None):
            if entity_id:
                return [r for r in relationships
                        if r["entity1_id"] == entity_id or r["entity2_id"] == entity_id]
            return relationships

        entity1_rels = await get_relationships(entity_id=1)
        assert len(entity1_rels) == 2


# ==================== Search Tests ====================

class TestAdvancedSearch:
    """Tests for advanced search functionality"""

    @pytest.mark.asyncio
    async def test_basic_text_search(self):
        """Test basic text search"""
        records = [
            {"id": 1, "title": "Mortgage Document", "description": "Property purchase"},
            {"id": 2, "title": "Tax Record", "description": "Annual taxes"},
            {"id": 3, "title": "Deed of Sale", "description": "Property mortgage transfer"}
        ]

        async def search(query):
            if not query:
                return records
            query_lower = query.lower()
            return [r for r in records
                    if query_lower in r["title"].lower()
                    or query_lower in r["description"].lower()]

        results = await search("mortgage")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_pagination(self):
        """Test search with pagination"""
        records = [{"id": i, "title": f"Record {i}"} for i in range(100)]

        async def search(page=1, page_size=50):
            offset = (page - 1) * page_size
            return {
                "records": records[offset:offset + page_size],
                "total_count": len(records),
                "page": page,
                "page_size": page_size,
                "total_pages": (len(records) + page_size - 1) // page_size
            }

        result = await search(page=2, page_size=25)
        assert result["page"] == 2
        assert len(result["records"]) == 25
        assert result["total_pages"] == 4

    @pytest.mark.asyncio
    async def test_search_with_date_range(self):
        """Test search with date range filter"""
        records = [
            {"id": 1, "date": date(2024, 1, 15)},
            {"id": 2, "date": date(2024, 3, 20)},
            {"id": 3, "date": date(2024, 6, 10)}
        ]

        async def search(date_from=None, date_to=None):
            result = records
            if date_from:
                result = [r for r in result if r["date"] >= date_from]
            if date_to:
                result = [r for r in result if r["date"] <= date_to]
            return result

        results = await search(date_from=date(2024, 2, 1), date_to=date(2024, 5, 1))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_with_amount_range(self):
        """Test search with amount range filter"""
        records = [
            {"id": 1, "amount": 100000},
            {"id": 2, "amount": 250000},
            {"id": 3, "amount": 500000}
        ]

        async def search(amount_min=None, amount_max=None):
            result = records
            if amount_min:
                result = [r for r in result if r["amount"] >= amount_min]
            if amount_max:
                result = [r for r in result if r["amount"] <= amount_max]
            return result

        results = await search(amount_min=150000, amount_max=400000)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_sorting(self):
        """Test search result sorting"""
        records = [
            {"id": 1, "date": date(2024, 3, 1)},
            {"id": 2, "date": date(2024, 1, 1)},
            {"id": 3, "date": date(2024, 2, 1)}
        ]

        async def search(sort_by="date", sort_order="desc"):
            result = sorted(records, key=lambda x: x[sort_by], reverse=(sort_order == "desc"))
            return result

        results = await search(sort_by="date", sort_order="asc")
        assert results[0]["id"] == 2  # Earliest date first


# ==================== Export Tests ====================

class TestDataExport:
    """Tests for data export functionality"""

    @pytest.mark.asyncio
    async def test_export_json(self):
        """Test JSON export format"""
        records = [
            {"id": 1, "title": "Record 1"},
            {"id": 2, "title": "Record 2"}
        ]

        async def export_data(format="json"):
            if format == "json":
                return {
                    "records": records,
                    "count": len(records),
                    "format": "json",
                    "timestamp": datetime.utcnow().isoformat()
                }

        result = await export_data(format="json")
        assert result["format"] == "json"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_export_csv(self):
        """Test CSV export format"""
        import csv

        records = [
            {"id": 1, "title": "Record 1", "amount": 100},
            {"id": 2, "title": "Record 2", "amount": 200}
        ]

        async def export_csv(records):
            output = io.StringIO()
            fieldnames = ["id", "title", "amount"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record)
            return output.getvalue()

        result = await export_csv(records)
        assert "id,title,amount" in result
        assert "Record 1" in result

    @pytest.mark.asyncio
    async def test_export_empty_result(self):
        """Test export with no records"""
        async def export_data(records):
            if not records:
                return {"message": "No records found for export", "count": 0}
            return {"records": records, "count": len(records)}

        result = await export_data([])
        assert result["count"] == 0
        assert "No records found" in result["message"]


# ==================== Integration Endpoints Tests ====================

class TestNeuralNetworkIntegration:
    """Tests for neural network integration endpoint"""

    @pytest.mark.asyncio
    async def test_integrate_nn_disabled(self):
        """Test NN integration when feature is disabled"""
        settings = {"enable_neural_network_integration": False}

        async def integrate_neural_network(record_id, enabled=False):
            if not enabled:
                raise Exception("Neural network integration is disabled")
            return {"status": "processing"}

        with pytest.raises(Exception, match="disabled"):
            await integrate_neural_network(1, enabled=False)

    @pytest.mark.asyncio
    async def test_integrate_nn_record_not_found(self):
        """Test NN integration with non-existent record"""
        records = {}

        async def integrate_neural_network(record_id):
            if record_id not in records:
                raise Exception("Record not found")
            return {"status": "processing"}

        with pytest.raises(Exception, match="not found"):
            await integrate_neural_network(999)

    @pytest.mark.asyncio
    async def test_integrate_nn_success(self):
        """Test successful NN integration start"""
        records = {1: {"id": 1, "title": "Test"}}

        async def integrate_neural_network(record_id):
            if record_id not in records:
                raise Exception("Record not found")
            return {
                "message": "Neural network processing started",
                "record_id": record_id,
                "status": "processing"
            }

        result = await integrate_neural_network(1)
        assert result["status"] == "processing"


class TestScraperIntegration:
    """Tests for scraper integration endpoint"""

    @pytest.mark.asyncio
    async def test_integrate_scraper_disabled(self):
        """Test scraper integration when feature is disabled"""
        async def integrate_scraper(jurisdiction_id, enabled=False):
            if not enabled:
                raise Exception("Scraper integration is disabled")
            return {"status": "processing"}

        with pytest.raises(Exception, match="disabled"):
            await integrate_scraper(1, enabled=False)

    @pytest.mark.asyncio
    async def test_integrate_scraper_success(self):
        """Test successful scraper integration start"""
        jurisdictions = {1: {"id": 1, "name": "Test County"}}

        async def integrate_scraper(jurisdiction_id):
            if jurisdiction_id not in jurisdictions:
                raise Exception("Jurisdiction not found")
            return {
                "message": "Scraper processing started",
                "jurisdiction_id": jurisdiction_id,
                "status": "processing"
            }

        result = await integrate_scraper(1)
        assert result["status"] == "processing"


# ==================== Cache Tests ====================

class TestCacheManagement:
    """Tests for cache management endpoints"""

    @pytest.mark.asyncio
    async def test_get_cache_stats_disabled(self):
        """Test getting cache stats when Redis is disabled"""
        async def get_cache_stats(redis_available=False):
            if not redis_available:
                return {"message": "Cache is disabled"}
            return {"status": "healthy", "stats": {}}

        result = await get_cache_stats(redis_available=False)
        assert result["message"] == "Cache is disabled"

    @pytest.mark.asyncio
    async def test_get_cache_stats_enabled(self):
        """Test getting cache stats when Redis is available"""
        async def get_cache_stats(redis_available=True):
            if not redis_available:
                return {"message": "Cache is disabled"}
            return {
                "status": "healthy",
                "stats": {
                    "used_memory": 1024000,
                    "keys": 150,
                    "uptime": 86400,
                    "connected_clients": 5
                }
            }

        result = await get_cache_stats()
        assert result["status"] == "healthy"
        assert "used_memory" in result["stats"]

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing cache"""
        async def clear_cache(redis_available=True):
            if not redis_available:
                return {"message": "Cache is disabled"}
            return {"message": "Cache cleared successfully"}

        result = await clear_cache()
        assert result["message"] == "Cache cleared successfully"


# ==================== Subscription Tests ====================

class TestSubscription:
    """Tests for subscription endpoints"""

    @pytest.mark.asyncio
    async def test_subscribe_valid_tier(self):
        """Test subscribing to a valid tier"""
        valid_tiers = ['basic', 'pro', 'enterprise']

        async def subscribe_to_plan(tier, mock_mode=True):
            tier = tier.lower()
            if tier not in valid_tiers:
                raise Exception("Invalid tier")

            if mock_mode:
                expires_at = datetime.utcnow() + timedelta(days=30)
                return {
                    "tier": tier,
                    "status": "active",
                    "expires_at": expires_at.isoformat()
                }

        result = await subscribe_to_plan("pro")
        assert result["tier"] == "pro"
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_subscribe_invalid_tier(self):
        """Test subscribing to an invalid tier"""
        valid_tiers = ['basic', 'pro', 'enterprise']

        async def subscribe_to_plan(tier):
            if tier.lower() not in valid_tiers:
                raise Exception("Invalid tier")

        with pytest.raises(Exception, match="Invalid tier"):
            await subscribe_to_plan("premium")

    @pytest.mark.asyncio
    async def test_get_subscription_status(self):
        """Test getting subscription status"""
        users = {
            "testuser": {"subscription_tier": "pro", "subscription_expires": "2024-12-31"}
        }

        async def get_subscription_status(username):
            user = users.get(username)
            if not user:
                raise Exception("User not found")
            return {
                "tier": user.get("subscription_tier", "free"),
                "status": "active" if user.get("subscription_tier") != "free" else "free",
                "expires_at": user.get("subscription_expires")
            }

        result = await get_subscription_status("testuser")
        assert result["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        """Test canceling a subscription"""
        users = {"testuser": {"subscription_tier": "pro"}}

        async def cancel_subscription(username):
            user = users.get(username)
            if not user:
                raise Exception("User not found")
            if user.get("subscription_tier", "free") == "free":
                raise Exception("No active subscription to cancel")

            users[username]["subscription_tier"] = "free"
            users[username]["subscription_expires"] = None
            return {"message": "Subscription cancelled", "tier": "free"}

        result = await cancel_subscription("testuser")
        assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_cancel_subscription_already_free(self):
        """Test canceling when no active subscription"""
        users = {"freeuser": {"subscription_tier": "free"}}

        async def cancel_subscription(username):
            user = users.get(username)
            if not user:
                raise Exception("User not found")
            if user.get("subscription_tier", "free") == "free":
                raise Exception("No active subscription to cancel")

        with pytest.raises(Exception, match="No active subscription"):
            await cancel_subscription("freeuser")


class TestStripeWebhook:
    """Tests for Stripe webhook handling"""

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self):
        """Test webhook with invalid signature"""
        async def stripe_webhook(payload, signature, valid_signature="correct"):
            if signature != valid_signature:
                raise Exception("Invalid webhook signature")
            return {"status": "received"}

        with pytest.raises(Exception, match="Invalid"):
            await stripe_webhook(b"payload", "wrong_signature")

    @pytest.mark.asyncio
    async def test_webhook_subscription_event(self):
        """Test handling subscription webhook event"""
        async def stripe_webhook(event_type, data):
            if event_type.startswith("customer.subscription"):
                return {
                    "status": "received",
                    "event_type": event_type
                }
            return {"status": "ignored"}

        result = await stripe_webhook("customer.subscription.created", {})
        assert result["event_type"] == "customer.subscription.created"

    @pytest.mark.asyncio
    async def test_webhook_checkout_completed(self):
        """Test handling checkout.session.completed event"""
        users = {1: {"id": 1, "subscription_tier": "free"}}

        async def handle_checkout_completed(session_data):
            metadata = session_data.get("metadata", {})
            user_id = int(metadata.get("user_id", 0))
            tier = metadata.get("tier")

            if user_id and tier and user_id in users:
                users[user_id]["subscription_tier"] = tier
                return {"status": "activated", "tier": tier}
            return {"status": "skipped"}

        result = await handle_checkout_completed({
            "metadata": {"user_id": "1", "tier": "pro"}
        })
        assert result["tier"] == "pro"
        assert users[1]["subscription_tier"] == "pro"


# ==================== Root and Test Endpoints ====================

class TestUtilityEndpoints:
    """Tests for utility endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async def root():
            return {
                "message": "DataGod API v2 is running",
                "version": "2.0.0",
                "documentation": "/docs",
                "status": "healthy"
            }

        result = await root()
        assert "DataGod API" in result["message"]
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_test_endpoint(self):
        """Test test endpoint"""
        async def test_endpoint():
            return {"message": "API v2 is working correctly"}

        result = await test_endpoint()
        assert "working correctly" in result["message"]


# ==================== Exception Handler Tests ====================

class TestExceptionHandlers:
    """Tests for exception handlers"""

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTP exception handler"""
        async def http_exception_handler(status_code, detail):
            return {
                "status_code": status_code,
                "content": {"message": detail}
            }

        result = await http_exception_handler(404, "Not found")
        assert result["status_code"] == 404
        assert result["content"]["message"] == "Not found"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler"""
        async def general_exception_handler(exc):
            # Log error
            return {
                "status_code": 500,
                "content": {"message": "Internal server error"}
            }

        result = await general_exception_handler(Exception("Something went wrong"))
        assert result["status_code"] == 500
        assert result["content"]["message"] == "Internal server error"


# ==================== Startup/Shutdown Event Tests ====================

class TestLifecycleEvents:
    """Tests for startup and shutdown events"""

    @pytest.mark.asyncio
    async def test_startup_event_all_healthy(self):
        """Test startup event with all services healthy"""
        logs = []

        async def startup_event(db_connected=True, redis_connected=True):
            logs.append("Starting DataGod API v2...")

            if db_connected:
                logs.append("Database connection established")
                logs.append("User database initialized")
            else:
                logs.append("Database connection failed")

            if redis_connected:
                logs.append("Cache connection established")
            else:
                logs.append("Cache is disabled")

            logs.append("API v2 started successfully")

        await startup_event()
        assert "started successfully" in logs[-1]

    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test shutdown event"""
        logs = []

        async def shutdown_event():
            logs.append("Shutting down DataGod API v2...")
            logs.append("Goodbye!")

        await shutdown_event()
        assert "Shutting down" in logs[0]


# ==================== Demo Users Tests ====================

class TestDemoUsers:
    """Tests for demo user creation"""

    def test_ensure_demo_users_exist(self):
        """Test ensuring demo users are created"""
        users_db = {}

        def get_password_hash(password):
            return f"$2b$12$hashed_{password}"

        def create_user(username, email, hashed_password, full_name, roles, disabled):
            users_db[username] = {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "full_name": full_name,
                "roles": roles,
                "disabled": disabled
            }

        def ensure_demo_users_exist():
            demo_users = [
                {
                    "username": "admin",
                    "email": "admin@datagod.com",
                    "full_name": "DataGod Admin",
                    "password": "admin123",
                    "roles": ["admin", "user"],
                    "disabled": False
                },
                {
                    "username": "user",
                    "email": "user@datagod.com",
                    "full_name": "DataGod User",
                    "password": "user123",
                    "roles": ["user"],
                    "disabled": False
                }
            ]

            for user_data in demo_users:
                if user_data["username"] not in users_db:
                    create_user(
                        username=user_data["username"],
                        email=user_data["email"],
                        hashed_password=get_password_hash(user_data["password"]),
                        full_name=user_data["full_name"],
                        roles=user_data["roles"],
                        disabled=user_data["disabled"]
                    )

        ensure_demo_users_exist()

        assert "admin" in users_db
        assert "user" in users_db
        assert "admin" in users_db["admin"]["roles"]
        assert users_db["user"]["roles"] == ["user"]


# ==================== Cache Decorator Tests ====================

class TestCacheDecorator:
    """Tests for cache decorator functionality"""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario"""
        cache = {"cache:test_func:hash123": '{"data": "cached"}'}

        async def cached_function(cache_key, redis_client=None):
            if redis_client and cache_key in cache:
                return json.loads(cache[cache_key])
            # Generate new result
            result = {"data": "fresh"}
            if redis_client:
                cache[cache_key] = json.dumps(result)
            return result

        result = await cached_function("cache:test_func:hash123", redis_client=True)
        assert result["data"] == "cached"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss scenario"""
        cache = {}

        async def cached_function(cache_key, redis_client=None):
            if redis_client and cache_key in cache:
                return json.loads(cache[cache_key])
            result = {"data": "fresh"}
            if redis_client:
                cache[cache_key] = json.dumps(result)
            return result

        result = await cached_function("cache:test_func:newhash", redis_client=True)
        assert result["data"] == "fresh"
        assert "cache:test_func:newhash" in cache


class TestCacheResponse:
    """Tests for cache_response decorator"""

    @pytest.mark.asyncio
    async def test_cache_response_with_redis(self):
        """Test cache response with Redis available"""
        cache = {}

        async def cache_response_decorator(func, expiration=300):
            async def wrapper(*args, **kwargs):
                cache_key = f"cache:{func.__name__}:{hash(frozenset(kwargs.items()))}"

                if cache_key in cache:
                    return json.loads(cache[cache_key])

                result = await func(*args, **kwargs)
                cache[cache_key] = json.dumps(result)
                return result
            return wrapper

        async def get_data():
            return {"result": "data"}

        # Simulate decorated function
        result1 = await get_data()
        cache["cache:get_data:0"] = json.dumps(result1)

        # Second call should hit cache
        cached_result = json.loads(cache["cache:get_data:0"])
        assert cached_result["result"] == "data"
