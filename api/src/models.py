"""
Pydantic models for DataGod API v2
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum
from typing_extensions import Annotated

# Base models
class BaseAPIModel(BaseModel):
    """Base model for all API responses"""
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }

# Jurisdiction models
class JurisdictionBase(BaseAPIModel):
    """Base jurisdiction model - matches SQLAlchemy Jurisdiction model"""
    name: str = Field(..., example="Los Angeles County")
    state: Optional[str] = Field(None, example="CA")
    county: Optional[str] = Field(None, example="Los Angeles")
    type: Optional[str] = Field(None, example="county")
    api_available: Optional[bool] = Field(False, example=False)
    scraper_needed: Optional[bool] = Field(True, example=True)
    description: Optional[str] = Field(None, example="Los Angeles County jurisdiction")

class JurisdictionCreate(JurisdictionBase):
    """Jurisdiction creation model"""
    pass

class JurisdictionUpdate(BaseAPIModel):
    """Jurisdiction update model"""
    name: Optional[str] = Field(None, example="Updated County Name")
    state: Optional[str] = Field(None, example="CA")
    county: Optional[str] = Field(None, example="Updated County")
    type: Optional[str] = Field(None, example="county")
    api_available: Optional[bool] = Field(None, example=True)
    scraper_needed: Optional[bool] = Field(None, example=False)
    description: Optional[str] = Field(None, example="Updated description")

class JurisdictionResponse(JurisdictionBase):
    """Jurisdiction response model"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00")

# Data Source models
class DataSourceBase(BaseAPIModel):
    """Base data source model - matches SQLAlchemy DataSource model"""
    jurisdiction_id: int = Field(..., example=1)
    source_name: str = Field(..., example="California Property API")
    source_type: str = Field(..., example="api")
    api_endpoint: Optional[str] = Field(None, example="https://api.california.gov/property")
    api_key: Optional[str] = Field(None, example="your-api-key-here")
    status: Optional[str] = Field("active", example="active")
    description: Optional[str] = Field(None, example="California property records API")

class DataSourceCreate(DataSourceBase):
    """Data source creation model"""
    pass

class DataSourceUpdate(BaseAPIModel):
    """Data source update model"""
    source_name: Optional[str] = Field(None, example="Updated API Name")
    source_type: Optional[str] = Field(None, example="api")
    api_endpoint: Optional[str] = Field(None, example="https://updated-api.example.com")
    api_key: Optional[str] = Field(None, example="new-api-key")
    status: Optional[str] = Field(None, example="active")
    description: Optional[str] = Field(None, example="Updated description")

class DataSourceResponse(DataSourceBase):
    """Data source response model"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00")

# Record models
class RecordBase(BaseAPIModel):
    """Base record model - matches SQLAlchemy Record model"""
    jurisdiction_id: int = Field(..., example=1)
    data_source_id: int = Field(..., example=1)
    record_type: str = Field(..., example="mortgage")
    title: str = Field(..., example="Property Mortgage Record")
    description: Optional[str] = Field(None, example="Mortgage record for property at 123 Main St")
    amount: Optional[float] = Field(None, example=250000.0)
    date: Optional[datetime] = Field(None, example="2023-01-15T00:00:00")
    raw_data: Optional[Dict[str, Any]] = Field(None, example={"original_source": "county_records"})

    class Config:
        arbitrary_types_allowed = True

class RecordCreate(RecordBase):
    """Record creation model"""
    pass

class RecordUpdate(BaseAPIModel):
    """Record update model"""
    data_source_id: Optional[int] = Field(None, example=1)
    record_type: Optional[str] = Field(None, example="mortgage")
    title: Optional[str] = Field(None, example="Updated Mortgage Record")
    description: Optional[str] = Field(None, example="Updated mortgage record")
    amount: Optional[float] = Field(None, example=275000.0)
    date: Optional[datetime] = Field(None, example="2023-02-15T00:00:00")
    raw_data: Optional[Dict[str, Any]] = Field(None, example={"version": 2})

    class Config:
        arbitrary_types_allowed = True

class RecordResponse(RecordBase):
    """Record response model"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00")

# Entity models
class EntityBase(BaseAPIModel):
    """Base entity model - matches SQLAlchemy Entity model"""
    entity_name: str = Field(..., example="John Doe")
    entity_type: str = Field(..., example="person")
    address: Optional[str] = Field(None, example="123 Main St, Anytown, CA 90210")
    city: Optional[str] = Field(None, example="Anytown")
    state: Optional[str] = Field(None, example="CA")
    zip_code: Optional[str] = Field(None, example="90210")
    description: Optional[str] = Field(None, example="Property owner")

class EntityCreate(EntityBase):
    """Entity creation model"""
    pass

class EntityUpdate(BaseAPIModel):
    """Entity update model"""
    entity_name: Optional[str] = Field(None, example="Johnathan Doe")
    entity_type: Optional[str] = Field(None, example="person")
    address: Optional[str] = Field(None, example="456 Oak Ave, Anytown, CA 90210")
    city: Optional[str] = Field(None, example="Newtown")
    state: Optional[str] = Field(None, example="CA")
    zip_code: Optional[str] = Field(None, example="90211")
    description: Optional[str] = Field(None, example="Updated owner")

class EntityResponse(EntityBase):
    """Entity response model"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00")

# Relationship models
class RelationshipBase(BaseAPIModel):
    """Base relationship model - matches SQLAlchemy Relationship model"""
    entity1_id: int = Field(..., example=1)
    entity2_id: int = Field(..., example=2)
    record_id: int = Field(..., example=1)
    relationship_type: str = Field(..., example="owner")
    role1: Optional[str] = Field(None, example="seller")
    role2: Optional[str] = Field(None, example="buyer")
    context: Optional[str] = Field(None, example="Property sale transaction")
    evidence: Optional[Dict[str, Any]] = Field(None, example={"document": "deed"})
    confidence_score: Optional[float] = Field(1.0, example=0.95)
    status: Optional[str] = Field("active", example="active")

class RelationshipCreate(RelationshipBase):
    """Relationship creation model"""
    pass

class RelationshipUpdate(BaseAPIModel):
    """Relationship update model"""
    relationship_type: Optional[str] = Field(None, example="co-owner")
    role1: Optional[str] = Field(None, example="owner")
    role2: Optional[str] = Field(None, example="tenant")
    context: Optional[str] = Field(None, example="Updated context")
    evidence: Optional[Dict[str, Any]] = Field(None, example={"verified": True})
    confidence_score: Optional[float] = Field(None, example=0.98)
    status: Optional[str] = Field(None, example="active")

class RelationshipResponse(RelationshipBase):
    """Relationship response model"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00")

# User models
class UserBase(BaseAPIModel):
    """Base user model"""
    username: str = Field(..., example="johndoe")
    email: str = Field(..., example="john@example.com")
    full_name: Optional[str] = Field(None, example="John Doe")
    disabled: Optional[bool] = Field(None, example=False)
    roles: List[str] = Field(..., example=["user"])

class UserRegister(BaseAPIModel):
    """User registration model for public registration"""
    username: str = Field(..., min_length=3, max_length=50, example="johndoe")
    email: str = Field(..., example="john@example.com")
    password: str = Field(..., min_length=8, example="securepassword123")
    full_name: Optional[str] = Field(None, example="John Doe")

class UserCreate(BaseAPIModel):
    """User creation model (admin use)"""
    username: str = Field(..., example="johndoe")
    email: str = Field(..., example="john@example.com")
    password: str = Field(..., example="securepassword123")
    full_name: Optional[str] = Field(None, example="John Doe")
    roles: List[str] = Field(default=["user"], example=["user"])

class UserUpdate(BaseAPIModel):
    """User update model"""
    email: Optional[str] = Field(None, example="newemail@example.com")
    full_name: Optional[str] = Field(None, example="Johnathan Doe")
    password: Optional[str] = Field(None, example="newsecurepassword123")
    roles: Optional[List[str]] = Field(None, example=["user", "admin"])

class UserResponse(UserBase):
    """User response model"""
    pass

class UserInDB(UserBase):
    """User database model"""
    hashed_password: str = Field(..., example="hashed_password_here")

# Authentication models
class Token(BaseAPIModel):
    """Token response model"""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., example="bearer")
    expires_in: int = Field(..., example=1800)

class TokenData(BaseAPIModel):
    """Token data model"""
    username: Optional[str] = Field(None, example="johndoe")
    roles: List[str] = Field(..., example=["user"])

class LoginRequest(BaseAPIModel):
    """Login request model for JSON-based login"""
    username: str = Field(..., example="johndoe")
    password: str = Field(..., example="securepassword123")

class ForgotPasswordRequest(BaseAPIModel):
    """Forgot password request model"""
    email: str = Field(..., example="john@example.com")

class ResetPasswordRequest(BaseAPIModel):
    """Reset password request model"""
    token: str = Field(..., example="reset-token-here")
    new_password: str = Field(..., min_length=8, example="newsecurepassword123")

class MessageResponse(BaseAPIModel):
    """Simple message response"""
    message: str = Field(..., example="Operation completed successfully")

# Search models
class SearchQuery(BaseAPIModel):
    """Advanced search query model"""
    query: Optional[str] = Field(None, example="mortgage")
    jurisdiction_ids: Optional[List[int]] = Field(None, example=[1, 2, 3])
    record_types: Optional[List[str]] = Field(None, example=["mortgage", "property"])
    entity_types: Optional[List[str]] = Field(None, example=["person", "company"])
    date_from: Optional[date] = Field(None, example="2023-01-01")
    date_to: Optional[date] = Field(None, example="2023-12-31")
    amount_min: Optional[float] = Field(None, example=100000.0)
    amount_max: Optional[float] = Field(None, example=1000000.0)
    sort_by: Optional[str] = Field("date", example="date")
    sort_order: Optional[str] = Field("desc", example="desc")
    page: int = Field(1, example=1)
    page_size: int = Field(50, example=50)

class SearchResponse(BaseAPIModel):
    """Search response model"""
    records: List[RecordResponse] = Field(..., example=[])
    total_count: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=50)
    total_pages: int = Field(..., example=2)

# Export models
class ExportRequest(BaseAPIModel):
    """Export request model"""
    format: str = Field("json", example="json")
    query: Optional[SearchQuery] = Field(None, example=None)
    fields: Optional[List[str]] = Field(None, example=["id", "title", "amount"])

class ExportResponse(BaseAPIModel):
    """Export response model"""
    records: Optional[List[Dict[str, Any]]] = Field(None, example=[{"id": 1, "title": "Record 1"}])
    count: Optional[int] = Field(None, example=10)
    format: Optional[str] = Field(None, example="json")
    timestamp: Optional[datetime] = Field(None, example="2023-01-01T00:00:00")

# Enums
class RecordType(str, Enum):
    """Record type enum"""
    MORTGAGE = "mortgage"
    PROPERTY = "property"
    TAX = "tax"
    LEGAL = "legal"
    FINANCIAL = "financial"

class EntityType(str, Enum):
    """Entity type enum"""
    PERSON = "person"
    COMPANY = "company"
    PROPERTY = "property"
    GOVERNMENT = "government"

class RelationshipType(str, Enum):
    """Relationship type enum"""
    OWNER = "owner"
    TENANT = "tenant"
    EMPLOYEE = "employee"
    DIRECTOR = "director"
    PARTNER = "partner"
    FAMILY = "family"
    ASSOCIATE = "associate"

# Health and monitoring models
class HealthResponse(BaseAPIModel):
    """Health check response model"""
    status: str = Field(..., example="healthy")
    timestamp: datetime = Field(..., example="2023-01-01T00:00:00")
    database: str = Field(..., example="healthy")
    cache: str = Field(..., example="healthy")
    api_version: str = Field(..., example="2.0.0")

class MetricsResponse(BaseAPIModel):
    """Metrics response model"""
    status: str = Field(..., example="metrics available")
    timestamp: datetime = Field(..., example="2023-01-01T00:00:00")
    metrics: Dict[str, Any] = Field(..., example={
        "api_calls": 100,
        "database_queries": 500,
        "cache_hits": 75,
        "active_connections": 10
    })

# Error models
class ErrorResponse(BaseAPIModel):
    """Error response model"""
    message: str = Field(..., example="Error message here")
    detail: Optional[str] = Field(None, example="Detailed error information")
    status_code: Optional[int] = Field(None, example=400)

# Cache models
class CacheStatsResponse(BaseAPIModel):
    """Cache statistics response model"""
    status: str = Field(..., example="healthy")
    stats: Dict[str, Any] = Field(..., example={
        "used_memory": 1024,
        "keys": 100,
        "uptime": 3600,
        "connected_clients": 5
    })

# Integration models
class IntegrationResponse(BaseAPIModel):
    """Integration response model"""
    message: str = Field(..., example="Integration started")
    record_id: Optional[int] = Field(None, example=1)
    jurisdiction_id: Optional[int] = Field(None, example=1)
    status: str = Field(..., example="processing")

# Pagination models
class PaginatedResponse(BaseAPIModel):
    """Pagination response model"""
    items: List[Any] = Field(..., example=[])
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=50)
    pages: int = Field(..., example=2)

# API Info models
class APIInfoResponse(BaseAPIModel):
    """API information response model"""
    message: str = Field(..., example="DataGod API v2 is running")
    version: str = Field(..., example="2.0.0")
    documentation: str = Field(..., example="/docs")
    status: str = Field(..., example="healthy")
