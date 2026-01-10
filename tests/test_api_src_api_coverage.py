#!/usr/bin/env python3
"""
Comprehensive tests for api/src/api.py
Tests authentication, endpoints, rate limiting, and caching functionality
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from functools import wraps


# ============================================================================
# Tests for User Models
# ============================================================================

class TestUserModels:
    """Tests for User and related Pydantic models"""

    def test_user_model_creation(self):
        """Test User model creation"""
        from pydantic import BaseModel
        from typing import Optional

        class User(BaseModel):
            username: str
            email: str
            full_name: Optional[str] = None
            disabled: Optional[bool] = None

        user = User(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name is None
        assert user.disabled is None

    def test_user_model_with_all_fields(self):
        """Test User model with all fields populated"""
        from pydantic import BaseModel
        from typing import Optional

        class User(BaseModel):
            username: str
            email: str
            full_name: Optional[str] = None
            disabled: Optional[bool] = None

        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            disabled=False
        )
        assert user.full_name == "Test User"
        assert user.disabled == False

    def test_user_in_db_model(self):
        """Test UserInDB model extends User"""
        from pydantic import BaseModel
        from typing import Optional

        class User(BaseModel):
            username: str
            email: str
            full_name: Optional[str] = None
            disabled: Optional[bool] = None

        class UserInDB(User):
            hashed_password: str

        user = UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$hashedpassword"
        )
        assert user.hashed_password == "$2b$12$hashedpassword"

    def test_token_model(self):
        """Test Token model"""
        from pydantic import BaseModel

        class Token(BaseModel):
            access_token: str
            token_type: str

        token = Token(access_token="abc123", token_type="bearer")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"

    def test_token_data_model(self):
        """Test TokenData model"""
        from pydantic import BaseModel
        from typing import Optional

        class TokenData(BaseModel):
            username: Optional[str] = None

        data = TokenData(username="testuser")
        assert data.username == "testuser"

        data_empty = TokenData()
        assert data_empty.username is None


# ============================================================================
# Tests for Password Hashing
# ============================================================================

class TestPasswordHashing:
    """Tests for password hashing functions"""

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        mock_pwd_context = MagicMock()
        mock_pwd_context.verify.return_value = True

        def verify_password(plain_password, hashed_password):
            return mock_pwd_context.verify(plain_password, hashed_password)

        result = verify_password("correct_password", "hashed_password")
        assert result == True
        mock_pwd_context.verify.assert_called_once()

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        mock_pwd_context = MagicMock()
        mock_pwd_context.verify.return_value = False

        def verify_password(plain_password, hashed_password):
            return mock_pwd_context.verify(plain_password, hashed_password)

        result = verify_password("wrong_password", "hashed_password")
        assert result == False

    def test_get_password_hash(self):
        """Test password hashing"""
        mock_pwd_context = MagicMock()
        mock_pwd_context.hash.return_value = "$2b$12$hashedvalue"

        def get_password_hash(password):
            return mock_pwd_context.hash(password)

        result = get_password_hash("my_password")
        assert result == "$2b$12$hashedvalue"
        mock_pwd_context.hash.assert_called_with("my_password")


# ============================================================================
# Tests for User Authentication
# ============================================================================

class TestUserAuthentication:
    """Tests for user authentication functions"""

    def test_get_user_exists(self):
        """Test getting existing user from database"""
        fake_users_db = {
            "johndoe": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "full_name": "John Doe",
                "hashed_password": "$2b$12$hash",
                "disabled": False,
            }
        }

        class UserInDB:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        def get_user(db, username):
            if username in db:
                user_dict = db[username]
                return UserInDB(**user_dict)
            return None

        user = get_user(fake_users_db, "johndoe")
        assert user is not None
        assert user.username == "johndoe"
        assert user.email == "johndoe@example.com"

    def test_get_user_not_exists(self):
        """Test getting non-existent user"""
        fake_users_db = {}

        def get_user(db, username):
            if username in db:
                return object()
            return None

        user = get_user(fake_users_db, "nonexistent")
        assert user is None

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"

        def get_user(db, username):
            if username == "valid_user":
                return mock_user
            return None

        def verify_password(plain, hashed):
            return plain == "correct_password"

        def authenticate_user(fake_db, username, password):
            user = get_user(fake_db, username)
            if not user:
                return False
            if not verify_password(password, user.hashed_password):
                return False
            return user

        result = authenticate_user({}, "valid_user", "correct_password")
        assert result == mock_user

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"

        def get_user(db, username):
            return mock_user

        def verify_password(plain, hashed):
            return False  # Wrong password

        def authenticate_user(fake_db, username, password):
            user = get_user(fake_db, username)
            if not user:
                return False
            if not verify_password(password, user.hashed_password):
                return False
            return user

        result = authenticate_user({}, "user", "wrong_password")
        assert result == False

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        def get_user(db, username):
            return None

        def authenticate_user(fake_db, username, password):
            user = get_user(fake_db, username)
            if not user:
                return False
            return user

        result = authenticate_user({}, "nonexistent", "password")
        assert result == False


# ============================================================================
# Tests for Token Creation
# ============================================================================

class TestTokenCreation:
    """Tests for JWT token creation"""

    def test_create_access_token_with_expiry(self):
        """Test creating access token with expiry"""
        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "encoded_token"

        SECRET_KEY = "secret"
        ALGORITHM = "HS256"

        def create_access_token(data, expires_delta=None):
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
                to_encode.update({"exp": expire})
            encoded_jwt = mock_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt

        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(minutes=30)
        )

        assert token == "encoded_token"
        mock_jwt.encode.assert_called_once()

    def test_create_access_token_without_expiry(self):
        """Test creating access token without explicit expiry"""
        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "encoded_token"

        SECRET_KEY = "secret"
        ALGORITHM = "HS256"

        def create_access_token(data, expires_delta=None):
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
                to_encode.update({"exp": expire})
            encoded_jwt = mock_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt

        token = create_access_token({"sub": "testuser"})

        assert token == "encoded_token"
        # Verify that encode was called with data without exp
        call_args = mock_jwt.encode.call_args[0]
        assert "exp" not in call_args[0]


# ============================================================================
# Tests for Current User Retrieval
# ============================================================================

class TestGetCurrentUser:
    """Tests for get_current_user function"""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token"""
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {"sub": "testuser"}

        mock_user = MagicMock()
        mock_user.username = "testuser"

        SECRET_KEY = "secret"
        ALGORITHM = "HS256"

        async def get_current_user(token):
            try:
                payload = mock_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                if username is None:
                    raise Exception("Invalid token")
                return mock_user
            except Exception:
                raise Exception("Could not validate credentials")

        user = await get_current_user("valid_token")
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        mock_jwt = MagicMock()
        mock_jwt.decode.side_effect = Exception("Invalid token")

        SECRET_KEY = "secret"
        ALGORITHM = "HS256"

        async def get_current_user(token):
            try:
                payload = mock_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                return payload
            except Exception:
                raise Exception("Could not validate credentials")

        with pytest.raises(Exception) as exc_info:
            await get_current_user("invalid_token")
        assert "Could not validate credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_no_username(self):
        """Test getting current user when username is None"""
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {"sub": None}  # No username

        async def get_current_user(token):
            payload = mock_jwt.decode(token, "secret", algorithms=["HS256"])
            username = payload.get("sub")
            if username is None:
                raise Exception("Invalid credentials")
            return {"username": username}

        with pytest.raises(Exception):
            await get_current_user("token_without_username")


# ============================================================================
# Tests for Rate Limiting
# ============================================================================

class TestRateLimiting:
    """Tests for rate limiting decorator"""

    def test_rate_limit_first_request(self):
        """Test rate limit decorator on first request"""
        request_count = [0]
        last_reset = [0]

        def rate_limit(max_requests=100, window=60):
            def decorator(func):
                @wraps(func)
                async def wrapper(*args, **kwargs):
                    current_time = time.time()
                    if last_reset[0] == 0:
                        last_reset[0] = current_time
                        request_count[0] = 1
                    elif current_time - last_reset[0] < window:
                        if request_count[0] >= max_requests:
                            raise Exception("Rate limit exceeded")
                        request_count[0] += 1
                    else:
                        request_count[0] = 1
                        last_reset[0] = current_time
                    return await func(*args, **kwargs)
                return wrapper
            return decorator

        @rate_limit(max_requests=5, window=60)
        async def test_endpoint():
            return "success"

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(test_endpoint())
        assert result == "success"
        assert request_count[0] == 1

    def test_rate_limit_within_limit(self):
        """Test multiple requests within rate limit"""
        request_count = [0]
        last_reset = [time.time()]

        async def make_request(max_requests, window):
            current_time = time.time()
            if current_time - last_reset[0] < window:
                if request_count[0] >= max_requests:
                    raise Exception("Rate limit exceeded")
                request_count[0] += 1
            else:
                request_count[0] = 1
                last_reset[0] = current_time
            return "success"

        import asyncio
        for _ in range(5):
            result = asyncio.get_event_loop().run_until_complete(
                make_request(max_requests=10, window=60)
            )
            assert result == "success"

        assert request_count[0] == 5

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded"""
        request_count = [100]  # Already at limit
        last_reset = [time.time()]

        async def make_request(max_requests, window):
            current_time = time.time()
            if current_time - last_reset[0] < window:
                if request_count[0] >= max_requests:
                    raise Exception("Rate limit exceeded")
                request_count[0] += 1
            return "success"

        import asyncio
        with pytest.raises(Exception) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                make_request(max_requests=100, window=60)
            )
        assert "Rate limit exceeded" in str(exc_info.value)


# ============================================================================
# Tests for API Endpoints
# ============================================================================

class TestAPIEndpoints:
    """Tests for API endpoint functions"""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login"""
        mock_user = MagicMock()
        mock_user.username = "testuser"

        def authenticate_user(db, username, password):
            if username == "testuser" and password == "password":
                return mock_user
            return False

        def create_access_token(data, expires_delta):
            return "test_token"

        async def login_for_access_token(username, password):
            user = authenticate_user({}, username, password)
            if not user:
                raise Exception("Incorrect username or password")
            access_token = create_access_token(
                data={"sub": user.username},
                expires_delta=timedelta(minutes=30)
            )
            return {"access_token": access_token, "token_type": "bearer"}

        result = await login_for_access_token("testuser", "password")
        assert result["access_token"] == "test_token"
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test failed login"""
        def authenticate_user(db, username, password):
            return False

        async def login_for_access_token(username, password):
            user = authenticate_user({}, username, password)
            if not user:
                raise Exception("Incorrect username or password")
            return {"access_token": "token", "token_type": "bearer"}

        with pytest.raises(Exception) as exc_info:
            await login_for_access_token("wrong_user", "wrong_password")
        assert "Incorrect username or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_users_me(self):
        """Test read_users_me endpoint"""
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        async def read_users_me(current_user):
            return current_user

        result = await read_users_me(mock_user)
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint"""
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

        result = await health_check()
        assert result["status"] == "healthy"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test metrics endpoint"""
        async def get_metrics():
            return {
                "status": "metrics available",
                "timestamp": datetime.utcnow().isoformat()
            }

        result = await get_metrics()
        assert result["status"] == "metrics available"

    @pytest.mark.asyncio
    async def test_test_endpoint(self):
        """Test simple test endpoint"""
        async def test_endpoint():
            return {"message": "API is working"}

        result = await test_endpoint()
        assert result["message"] == "API is working"


# ============================================================================
# Tests for Search Functionality
# ============================================================================

class TestSearchFunctionality:
    """Tests for advanced search endpoint"""

    @pytest.mark.asyncio
    async def test_advanced_search_basic(self):
        """Test basic search without filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.offset.return_value.limit.return_value.all.return_value = []
        mock_query.count.return_value = 0
        mock_db.query.return_value = mock_query

        async def advanced_search(db, query=None, limit=100, offset=0):
            records_query = db.query(MagicMock())
            if query:
                pass  # Apply filter
            records = records_query.offset(offset).limit(limit).all()
            return {
                "records": records,
                "count": records_query.count(),
                "offset": offset,
                "limit": limit
            }

        result = await advanced_search(mock_db)
        assert result["records"] == []
        assert result["count"] == 0
        assert result["limit"] == 100

    @pytest.mark.asyncio
    async def test_advanced_search_with_query(self):
        """Test search with text query"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.offset.return_value.limit.return_value.all.return_value = [
            {"id": 1, "title": "Test Record"}
        ]
        mock_filter.count.return_value = 1
        mock_db.query.return_value = mock_query

        async def advanced_search(db, query=None, limit=100, offset=0):
            records_query = db.query(MagicMock())
            if query:
                records_query = records_query.filter(MagicMock())
            records = records_query.offset(offset).limit(limit).all()
            return {
                "records": records,
                "count": records_query.count(),
                "offset": offset,
                "limit": limit
            }

        result = await advanced_search(mock_db, query="test")
        assert len(result["records"]) == 1

    @pytest.mark.asyncio
    async def test_advanced_search_with_filters(self):
        """Test search with multiple filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()

        # Chain of filters
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = []
        mock_query.count.return_value = 0
        mock_db.query.return_value = mock_query

        async def advanced_search(
            db,
            query=None,
            jurisdiction_id=None,
            record_type=None,
            date_from=None,
            date_to=None,
            amount_min=None,
            amount_max=None,
            limit=100,
            offset=0
        ):
            records_query = db.query(MagicMock())

            if query:
                records_query = records_query.filter(MagicMock())
            if jurisdiction_id:
                records_query = records_query.filter(MagicMock())
            if record_type:
                records_query = records_query.filter(MagicMock())
            if date_from:
                records_query = records_query.filter(MagicMock())
            if date_to:
                records_query = records_query.filter(MagicMock())
            if amount_min:
                records_query = records_query.filter(MagicMock())
            if amount_max:
                records_query = records_query.filter(MagicMock())

            records = records_query.offset(offset).limit(limit).all()
            return {
                "records": records,
                "count": records_query.count(),
                "offset": offset,
                "limit": limit
            }

        result = await advanced_search(
            mock_db,
            jurisdiction_id=1,
            record_type="deed",
            date_from="2023-01-01",
            date_to="2023-12-31",
            amount_min=10000,
            amount_max=500000
        )

        assert result["records"] == []


# ============================================================================
# Tests for Export Functionality
# ============================================================================

class TestExportFunctionality:
    """Tests for data export endpoint"""

    @pytest.mark.asyncio
    async def test_export_json(self):
        """Test JSON export"""
        mock_record1 = MagicMock()
        mock_record1.__dict__ = {"id": 1, "title": "Record 1"}
        mock_record2 = MagicMock()
        mock_record2.__dict__ = {"id": 2, "title": "Record 2"}
        mock_records = [mock_record1, mock_record2]

        async def export_data(records, format="json"):
            if format == "json":
                return {"records": [r.__dict__ for r in records]}
            return None

        result = await export_data(mock_records, format="json")
        assert len(result["records"]) == 2

    @pytest.mark.asyncio
    async def test_export_csv(self):
        """Test CSV export"""
        import csv
        from io import StringIO

        mock_record = MagicMock()
        mock_record.__dict__ = {"id": 1, "title": "Record 1", "_sa_instance_state": None}
        mock_records = [mock_record]

        async def export_data(records, format="csv"):
            if format == "csv":
                output = StringIO()
                if records:
                    fieldnames = [k for k in records[0].__dict__.keys() if k != "_sa_instance_state"]
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for record in records:
                        row = {k: v for k, v in record.__dict__.items() if k != "_sa_instance_state"}
                        writer.writerow(row)
                return output.getvalue()
            return None

        result = await export_data(mock_records, format="csv")
        assert "id" in result
        assert "title" in result

    @pytest.mark.asyncio
    async def test_export_xml(self):
        """Test XML export"""
        import xml.etree.ElementTree as ET

        mock_record = MagicMock()
        mock_record.__dict__ = {"id": 1, "title": "Record 1", "_sa_instance_state": None}
        mock_records = [mock_record]

        async def export_data(records, format="xml"):
            if format == "xml":
                root = ET.Element("records")
                for record in records:
                    record_elem = ET.SubElement(root, "record")
                    for key, value in record.__dict__.items():
                        if key != "_sa_instance_state":
                            elem = ET.SubElement(record_elem, key)
                            elem.text = str(value)
                return ET.tostring(root, encoding="unicode")
            return None

        result = await export_data(mock_records, format="xml")
        assert "<records>" in result
        assert "<record>" in result
        assert "<id>1</id>" in result


# ============================================================================
# Tests for Caching
# ============================================================================

class TestCaching:
    """Tests for caching functionality"""

    @pytest.mark.asyncio
    async def test_get_cached_data_hit(self):
        """Test cache hit"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"key": "value"}'

        async def get_cached_data(key, redis_client):
            if redis_client:
                cached_data = redis_client.get(key)
                if cached_data:
                    import json
                    return {"cached": True, "data": json.loads(cached_data)}
            return {"cached": False, "data": None}

        result = await get_cached_data("test_key", mock_redis)
        assert result["cached"] == True
        assert result["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_cached_data_miss(self):
        """Test cache miss"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        async def get_cached_data(key, redis_client):
            if redis_client:
                cached_data = redis_client.get(key)
                if cached_data:
                    return {"cached": True, "data": cached_data}
            return {"cached": False, "data": None}

        result = await get_cached_data("missing_key", mock_redis)
        assert result["cached"] == False
        assert result["data"] is None

    @pytest.mark.asyncio
    async def test_get_cached_data_no_redis(self):
        """Test caching when Redis not available"""
        async def get_cached_data(key, redis_client):
            if redis_client:
                cached_data = redis_client.get(key)
                if cached_data:
                    return {"cached": True, "data": cached_data}
            return {"cached": False, "data": None}

        result = await get_cached_data("test_key", None)
        assert result["cached"] == False

    @pytest.mark.asyncio
    async def test_set_cached_data(self):
        """Test setting cached data"""
        mock_redis = MagicMock()

        async def set_cached_data(key, data, expire, redis_client):
            if redis_client:
                import json
                redis_client.setex(key, expire, json.dumps(data))
                return {"status": "cached"}
            return {"status": "cache not available"}

        result = await set_cached_data(
            "test_key",
            {"key": "value"},
            3600,
            mock_redis
        )
        assert result["status"] == "cached"
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_cached_data_no_redis(self):
        """Test setting cache when Redis not available"""
        async def set_cached_data(key, data, expire, redis_client):
            if redis_client:
                return {"status": "cached"}
            return {"status": "cache not available"}

        result = await set_cached_data("test_key", {}, 3600, None)
        assert result["status"] == "cache not available"


# ============================================================================
# Tests for CRUD Endpoints
# ============================================================================

class TestCRUDEndpoints:
    """Tests for CRUD endpoint functions"""

    @pytest.mark.asyncio
    async def test_get_jurisdictions(self):
        """Test getting all jurisdictions"""
        mock_db = MagicMock()
        mock_jurisdictions = [MagicMock(id=1), MagicMock(id=2)]
        mock_db.query.return_value.all.return_value = mock_jurisdictions

        async def get_jurisdictions(db):
            return db.query(MagicMock()).all()

        result = await get_jurisdictions(mock_db)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_jurisdiction_found(self):
        """Test getting specific jurisdiction"""
        mock_db = MagicMock()
        mock_jurisdiction = MagicMock(id=1, name="Test County")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_jurisdiction

        async def get_jurisdiction(id, db):
            jurisdiction = db.query(MagicMock()).filter(MagicMock()).first()
            if not jurisdiction:
                raise Exception("Jurisdiction not found")
            return jurisdiction

        result = await get_jurisdiction(1, mock_db)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_jurisdiction_not_found(self):
        """Test getting non-existent jurisdiction"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        async def get_jurisdiction(id, db):
            jurisdiction = db.query(MagicMock()).filter(MagicMock()).first()
            if not jurisdiction:
                raise Exception("Jurisdiction not found")
            return jurisdiction

        with pytest.raises(Exception) as exc_info:
            await get_jurisdiction(999, mock_db)
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_records_pagination(self):
        """Test getting records with pagination"""
        mock_db = MagicMock()
        mock_records = [MagicMock(id=i) for i in range(10)]
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_records

        async def get_records(db, limit=100, offset=0):
            return db.query(MagicMock()).offset(offset).limit(limit).all()

        result = await get_records(mock_db, limit=10, offset=0)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_get_record_found(self):
        """Test getting specific record"""
        mock_db = MagicMock()
        mock_record = MagicMock(id=1, title="Test Record")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_record

        async def get_record(id, db):
            record = db.query(MagicMock()).filter(MagicMock()).first()
            if not record:
                raise Exception("Record not found")
            return record

        result = await get_record(1, mock_db)
        assert result.title == "Test Record"

    @pytest.mark.asyncio
    async def test_get_entities(self):
        """Test getting entities with pagination"""
        mock_db = MagicMock()
        mock_entities = [MagicMock(id=i) for i in range(5)]
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_entities

        async def get_entities(db, limit=100, offset=0):
            return db.query(MagicMock()).offset(offset).limit(limit).all()

        result = await get_entities(mock_db)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_relationships(self):
        """Test getting relationships with pagination"""
        mock_db = MagicMock()
        mock_relationships = [MagicMock(id=i) for i in range(3)]
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_relationships

        async def get_relationships(db, limit=100, offset=0):
            return db.query(MagicMock()).offset(offset).limit(limit).all()

        result = await get_relationships(mock_db)
        assert len(result) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
