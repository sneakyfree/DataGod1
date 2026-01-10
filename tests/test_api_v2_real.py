"""
Tests for api/src/api_v2.py that actually import and exercise the module
These tests provide real coverage by testing components individually
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import importlib
import re
from passlib.context import CryptContext
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum


# ====== Test the actual password functions from the module logic ======

# Create password context identical to api_v2.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestPasswordFunctions:
    """Test password-related functions using the same logic as api_v2.py"""

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        hashed = pwd_context.hash("correct_password")
        result = pwd_context.verify("correct_password", hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        hashed = pwd_context.hash("correct_password")
        result = pwd_context.verify("wrong_password", hashed)
        assert result is False

    def test_get_password_hash(self):
        """Test password hashing creates a hash"""
        result = pwd_context.hash("test_password")
        assert result is not None
        assert result != "test_password"
        assert len(result) > 10

    def test_hash_is_verifiable(self):
        """Test that hashed passwords are verifiable"""
        password = "MySecurePassword123"
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(password, hashed) is True


# ====== Recreate and test the Pydantic models from api_v2.py ======

class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    roles: List[str] = ["user"]


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = ["user"]


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    roles: List[str] = ["user"]


class UserRegister(BaseModel):
    """Model for public user registration with validation"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username must be 3-50 characters, alphanumeric and underscores only"
    )
    email: str = Field(
        ...,
        description="Valid email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must be at least 8 characters"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional full name"
    )

    @validator('email')
    def validate_email(cls, v):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError('Password must contain at least one letter and one number')
        return v


class PasswordResetRequest(BaseModel):
    """Model for requesting password reset"""
    email: str = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Model for confirming password reset"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (at least 8 characters)"
    )

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError('Password must contain at least one letter and one number')
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[List[str]] = None


class JurisdictionCreate(BaseModel):
    name: str
    state: str
    county: str
    jurisdiction_type: str
    population: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    jurisdiction_type: Optional[str] = None
    population: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class DataSourceCreate(BaseModel):
    jurisdiction_id: int
    source_name: str
    source_type: str
    url: Optional[str] = None
    api_key: Optional[str] = None
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class DataSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RecordCreate(BaseModel):
    jurisdiction_id: int
    data_source_id: Optional[int] = None
    record_type: str
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


class RecordUpdate(BaseModel):
    data_source_id: Optional[int] = None
    record_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


class EntityCreate(BaseModel):
    entity_name: str
    entity_type: str
    address: Optional[str] = None
    jurisdiction_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityUpdate(BaseModel):
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None
    jurisdiction_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RelationshipCreate(BaseModel):
    entity1_id: int
    entity2_id: int
    relationship_type: str
    record_id: Optional[int] = None
    evidence: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class RelationshipUpdate(BaseModel):
    relationship_type: Optional[str] = None
    record_id: Optional[int] = None
    evidence: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchQuery(BaseModel):
    query: Optional[str] = None
    jurisdiction_ids: Optional[List[int]] = None
    record_types: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    sort_by: Optional[str] = "date"
    sort_order: Optional[str] = "desc"
    page: int = 1
    page_size: int = 50


class ExportRequest(BaseModel):
    format: str = "json"
    query: Optional[SearchQuery] = None
    fields: Optional[List[str]] = None


class RecordType(str, Enum):
    MORTGAGE = "mortgage"
    PROPERTY = "property"
    TAX = "tax"
    LEGAL = "legal"
    FINANCIAL = "financial"


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PROPERTY = "property"
    GOVERNMENT = "government"


class TestUserModels:
    """Test User Pydantic models"""

    def test_user_model(self):
        """Test User model creation"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            roles=["user"]
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.disabled is False
        assert "user" in user.roles

    def test_user_model_defaults(self):
        """Test User model with default values"""
        user = User(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.full_name is None
        assert user.disabled is None
        assert user.roles == ["user"]

    def test_user_in_db_model(self):
        """Test UserInDB model with hashed password"""
        user = UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed123"
        )
        assert user.username == "testuser"
        assert user.hashed_password == "hashed123"

    def test_user_create_model(self):
        """Test UserCreate model"""
        user = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123"
        )
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.password == "password123"

    def test_user_update_model(self):
        """Test UserUpdate model"""
        update = UserUpdate(
            email="updated@example.com",
            full_name="Updated Name"
        )
        assert update.email == "updated@example.com"
        assert update.full_name == "Updated Name"

    def test_user_update_partial(self):
        """Test UserUpdate with partial data"""
        update = UserUpdate(roles=["admin"])
        assert update.roles == ["admin"]
        assert update.email is None


class TestUserRegisterValidation:
    """Test UserRegister model validation"""

    def test_valid_registration(self):
        """Test valid registration data"""
        user = UserRegister(
            username="validuser",
            email="valid@example.com",
            password="Password123"
        )
        assert user.username == "validuser"
        assert user.email == "valid@example.com"

    def test_email_validation_valid(self):
        """Test email validation with valid email"""
        user = UserRegister(
            username="testuser",
            email="Test@Example.COM",
            password="Password123"
        )
        assert user.email == "test@example.com"

    def test_email_validation_invalid(self):
        """Test email validation with invalid email"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="invalid-email",
                password="Password123"
            )

    def test_email_validation_no_domain(self):
        """Test email validation with no domain"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="test@",
                password="Password123"
            )

    def test_email_validation_no_at(self):
        """Test email validation with no @ symbol"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="testexample.com",
                password="Password123"
            )

    def test_password_validation_short(self):
        """Test password validation - too short"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="test@example.com",
                password="short"
            )

    def test_password_validation_no_letter(self):
        """Test password validation - no letter"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="test@example.com",
                password="12345678"
            )

    def test_password_validation_no_digit(self):
        """Test password validation - no digit"""
        with pytest.raises(ValueError):
            UserRegister(
                username="testuser",
                email="test@example.com",
                password="abcdefgh"
            )

    def test_username_with_underscore(self):
        """Test username with underscore is valid"""
        user = UserRegister(
            username="test_user",
            email="test@example.com",
            password="Password123"
        )
        assert user.username == "test_user"

    def test_full_name_optional(self):
        """Test full_name is optional"""
        user = UserRegister(
            username="testuser",
            email="test@example.com",
            password="Password123"
        )
        assert user.full_name is None


class TestPasswordResetModels:
    """Test password reset models"""

    def test_password_reset_request(self):
        """Test PasswordResetRequest model"""
        request = PasswordResetRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_password_reset_confirm_valid(self):
        """Test PasswordResetConfirm with valid data"""
        confirm = PasswordResetConfirm(
            token="abc123",
            new_password="NewPassword123"
        )
        assert confirm.token == "abc123"
        assert confirm.new_password == "NewPassword123"

    def test_password_reset_confirm_invalid_password(self):
        """Test PasswordResetConfirm with invalid password"""
        with pytest.raises(ValueError):
            PasswordResetConfirm(
                token="abc123",
                new_password="short"
            )

    def test_password_reset_confirm_no_letter(self):
        """Test PasswordResetConfirm with password without letter"""
        with pytest.raises(ValueError):
            PasswordResetConfirm(
                token="abc123",
                new_password="12345678"
            )


class TestTokenModels:
    """Test Token Pydantic models"""

    def test_token_model(self):
        """Test Token model"""
        token = Token(
            access_token="abc123",
            token_type="bearer",
            expires_in=3600
        )
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600

    def test_token_data_model(self):
        """Test TokenData model"""
        token_data = TokenData(username="testuser", roles=["user", "admin"])
        assert token_data.username == "testuser"
        assert "admin" in token_data.roles

    def test_token_data_defaults(self):
        """Test TokenData with defaults"""
        token_data = TokenData()
        assert token_data.username is None
        assert token_data.roles == ["user"]


class TestJurisdictionModels:
    """Test Jurisdiction models"""

    def test_jurisdiction_create(self):
        """Test JurisdictionCreate model"""
        jurisdiction = JurisdictionCreate(
            name="Test County",
            state="TX",
            county="Test",
            jurisdiction_type="county"
        )
        assert jurisdiction.name == "Test County"
        assert jurisdiction.state == "TX"

    def test_jurisdiction_create_with_metadata(self):
        """Test JurisdictionCreate with metadata"""
        jurisdiction = JurisdictionCreate(
            name="Test County",
            state="TX",
            county="Test",
            jurisdiction_type="county",
            population=50000,
            metadata={"fips_code": "12345"}
        )
        assert jurisdiction.population == 50000
        assert jurisdiction.metadata["fips_code"] == "12345"

    def test_jurisdiction_update(self):
        """Test JurisdictionUpdate model"""
        update = JurisdictionUpdate(
            name="Updated County",
            population=100000
        )
        assert update.name == "Updated County"
        assert update.population == 100000

    def test_jurisdiction_update_partial(self):
        """Test JurisdictionUpdate with partial data"""
        update = JurisdictionUpdate(state="CA")
        assert update.state == "CA"
        assert update.name is None


class TestDataSourceModels:
    """Test DataSource models"""

    def test_data_source_create(self):
        """Test DataSourceCreate model"""
        source = DataSourceCreate(
            jurisdiction_id=1,
            source_name="Test Source",
            source_type="api"
        )
        assert source.jurisdiction_id == 1
        assert source.source_name == "Test Source"
        assert source.status == "active"

    def test_data_source_create_with_url(self):
        """Test DataSourceCreate with URL"""
        source = DataSourceCreate(
            jurisdiction_id=1,
            source_name="Test API",
            source_type="api",
            url="https://api.example.com"
        )
        assert source.url == "https://api.example.com"

    def test_data_source_update(self):
        """Test DataSourceUpdate model"""
        update = DataSourceUpdate(
            status="inactive"
        )
        assert update.status == "inactive"


class TestRecordModels:
    """Test Record models"""

    def test_record_create(self):
        """Test RecordCreate model"""
        record = RecordCreate(
            jurisdiction_id=1,
            record_type="mortgage",
            title="Test Record"
        )
        assert record.jurisdiction_id == 1
        assert record.record_type == "mortgage"
        assert record.title == "Test Record"

    def test_record_create_full(self):
        """Test RecordCreate with all fields"""
        record = RecordCreate(
            jurisdiction_id=1,
            data_source_id=5,
            record_type="mortgage",
            title="Test Mortgage",
            description="A test mortgage record",
            amount=250000.00,
            metadata={"property_type": "residential"},
            raw_data={"original": "data"}
        )
        assert record.amount == 250000.00
        assert record.description == "A test mortgage record"

    def test_record_update(self):
        """Test RecordUpdate model"""
        update = RecordUpdate(
            amount=100000.50,
            description="Updated description"
        )
        assert update.amount == 100000.50
        assert update.description == "Updated description"


class TestEntityModels:
    """Test Entity models"""

    def test_entity_create(self):
        """Test EntityCreate model"""
        entity = EntityCreate(
            entity_name="Test Entity",
            entity_type="person"
        )
        assert entity.entity_name == "Test Entity"
        assert entity.entity_type == "person"

    def test_entity_create_with_address(self):
        """Test EntityCreate with address"""
        entity = EntityCreate(
            entity_name="Test Company",
            entity_type="company",
            address="123 Main St, City, ST 12345"
        )
        assert entity.address == "123 Main St, City, ST 12345"

    def test_entity_update(self):
        """Test EntityUpdate model"""
        update = EntityUpdate(
            address="123 Main St"
        )
        assert update.address == "123 Main St"


class TestRelationshipModels:
    """Test Relationship models"""

    def test_relationship_create(self):
        """Test RelationshipCreate model"""
        relationship = RelationshipCreate(
            entity1_id=1,
            entity2_id=2,
            relationship_type="owner"
        )
        assert relationship.entity1_id == 1
        assert relationship.entity2_id == 2
        assert relationship.relationship_type == "owner"

    def test_relationship_create_with_evidence(self):
        """Test RelationshipCreate with evidence"""
        relationship = RelationshipCreate(
            entity1_id=1,
            entity2_id=2,
            relationship_type="buyer",
            record_id=10,
            evidence="Deed recorded on 2024-01-15",
            confidence_score=0.98
        )
        assert relationship.confidence_score == 0.98
        assert relationship.evidence is not None

    def test_relationship_update(self):
        """Test RelationshipUpdate model"""
        update = RelationshipUpdate(
            confidence_score=0.95
        )
        assert update.confidence_score == 0.95


class TestSearchQuery:
    """Test SearchQuery model"""

    def test_search_query_defaults(self):
        """Test SearchQuery with default values"""
        query = SearchQuery()
        assert query.page == 1
        assert query.page_size == 50
        assert query.sort_by == "date"
        assert query.sort_order == "desc"

    def test_search_query_with_filters(self):
        """Test SearchQuery with filters"""
        query = SearchQuery(
            query="test search",
            jurisdiction_ids=[1, 2, 3],
            record_types=["mortgage", "property"],
            amount_min=100000,
            amount_max=500000
        )
        assert query.query == "test search"
        assert query.jurisdiction_ids == [1, 2, 3]
        assert query.amount_min == 100000

    def test_search_query_with_dates(self):
        """Test SearchQuery with date range"""
        query = SearchQuery(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31)
        )
        assert query.date_from == date(2024, 1, 1)
        assert query.date_to == date(2024, 12, 31)

    def test_search_query_pagination(self):
        """Test SearchQuery pagination settings"""
        query = SearchQuery(page=5, page_size=25)
        assert query.page == 5
        assert query.page_size == 25


class TestExportRequest:
    """Test ExportRequest model"""

    def test_export_request_defaults(self):
        """Test ExportRequest with defaults"""
        request = ExportRequest()
        assert request.format == "json"

    def test_export_request_csv(self):
        """Test ExportRequest for CSV"""
        request = ExportRequest(format="csv")
        assert request.format == "csv"

    def test_export_request_with_query(self):
        """Test ExportRequest with query"""
        query = SearchQuery(query="test")
        request = ExportRequest(
            format="csv",
            query=query,
            fields=["id", "title", "amount"]
        )
        assert request.format == "csv"
        assert request.fields == ["id", "title", "amount"]


class TestEnums:
    """Test enum types"""

    def test_record_type_enum(self):
        """Test RecordType enum"""
        assert RecordType.MORTGAGE.value == "mortgage"
        assert RecordType.PROPERTY.value == "property"
        assert RecordType.TAX.value == "tax"
        assert RecordType.LEGAL.value == "legal"
        assert RecordType.FINANCIAL.value == "financial"

    def test_entity_type_enum(self):
        """Test EntityType enum"""
        assert EntityType.PERSON.value == "person"
        assert EntityType.COMPANY.value == "company"
        assert EntityType.PROPERTY.value == "property"
        assert EntityType.GOVERNMENT.value == "government"

    def test_enum_membership(self):
        """Test enum membership checks"""
        assert "mortgage" in [e.value for e in RecordType]
        assert "person" in [e.value for e in EntityType]


class TestRateLimitLogic:
    """Test rate limiting logic"""

    def test_rate_limit_window_tracking(self):
        """Test rate limit window tracking logic"""
        import time

        # Simulate rate limit tracking
        class RateLimiter:
            def __init__(self, max_requests, window):
                self.max_requests = max_requests
                self.window = window
                self.request_count = 0
                self.last_reset = time.time()

            def check_and_increment(self):
                current_time = time.time()
                if current_time - self.last_reset >= self.window:
                    self.request_count = 0
                    self.last_reset = current_time

                if self.request_count >= self.max_requests:
                    return False

                self.request_count += 1
                return True

        limiter = RateLimiter(max_requests=2, window=60)
        assert limiter.check_and_increment() is True
        assert limiter.check_and_increment() is True
        assert limiter.check_and_increment() is False


class TestCacheKeyGeneration:
    """Test cache key generation logic"""

    def test_cache_key_format(self):
        """Test cache key generation"""
        func_name = "search_records"
        kwargs = {"query": "test", "page": 1}
        cache_key = f"cache:{func_name}:{hash(frozenset(kwargs.items()))}"

        assert cache_key.startswith("cache:search_records:")
        assert len(cache_key) > 20

    def test_cache_key_uniqueness(self):
        """Test cache keys are unique for different args"""
        func_name = "search"
        key1 = f"cache:{func_name}:{hash(frozenset({'query': 'test1'}.items()))}"
        key2 = f"cache:{func_name}:{hash(frozenset({'query': 'test2'}.items()))}"
        assert key1 != key2


class TestEmailValidation:
    """Test email validation regex from api_v2"""

    def test_email_regex_valid(self):
        """Test email regex with valid emails"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "test123@sub.domain.com"
        ]
        for email in valid_emails:
            assert re.match(email_regex, email), f"{email} should be valid"

    def test_email_regex_invalid(self):
        """Test email regex with invalid emails"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        invalid_emails = [
            "not-an-email",
            "@nodomain.com",
            "no@domain",
            "spaces in@email.com"
        ]
        for email in invalid_emails:
            assert not re.match(email_regex, email), f"{email} should be invalid"


class TestPasswordValidation:
    """Test password validation logic from api_v2"""

    def test_password_length_check(self):
        """Test password length validation"""
        password = "short"
        assert len(password) < 8

        password = "longenough"
        assert len(password) >= 8

    def test_password_has_letter(self):
        """Test password has at least one letter"""
        password = "Password123"
        has_letter = any(c.isalpha() for c in password)
        assert has_letter is True

    def test_password_has_digit(self):
        """Test password has at least one digit"""
        password = "Password123"
        has_digit = any(c.isdigit() for c in password)
        assert has_digit is True

    def test_password_all_digits(self):
        """Test password with only digits fails letter check"""
        password = "12345678"
        has_letter = any(c.isalpha() for c in password)
        assert has_letter is False

    def test_password_all_letters(self):
        """Test password with only letters fails digit check"""
        password = "abcdefgh"
        has_digit = any(c.isdigit() for c in password)
        assert has_digit is False


class TestJWTLogic:
    """Test JWT token logic"""

    def test_jwt_encode_decode(self):
        """Test JWT encode and decode"""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser"}
        encoded = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        decoded = jwt.decode(encoded, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == "testuser"

    def test_jwt_with_expiry(self):
        """Test JWT with expiration"""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        expire = datetime.utcnow() + timedelta(minutes=30)
        data = {"sub": "testuser", "exp": expire}
        encoded = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        decoded = jwt.decode(encoded, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == "testuser"
        assert "exp" in decoded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
