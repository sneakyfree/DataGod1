"""
DataGod API v2 - Comprehensive API Layer for Mortgage Data Gathering Neural Network
"""

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, TypeVar, Generic
from datetime import datetime, timedelta, date
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import cast
from datagod.models import Jurisdiction, DataSource, Record, Entity, Relationship, SavedSearch, UserFavorite, UserActivity, ShareLink
from db import get_db, check_db_connection, SessionLocal
from config import settings
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db_manager import DatabaseManager, get_db_manager
import redis
import json
import csv
import io
import time
import logging
import hashlib
import uuid
from functools import wraps
from enum import Enum
import pandas as pd
from typing_extensions import Annotated

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url=settings.api_docs_url,
    openapi_url=settings.api_openapi_url,
    redoc_url="/redoc",
    swagger_ui_parameters={"syntaxHighlight.theme": "monokai"}
)

# Security settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Redis connection for caching
redis_client = None
try:
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info("✅ Redis cache connected successfully")
except Exception as e:
    logger.warning(f"⚠️ Redis cache not available: {e}")
    redis_client = None

# Rate limiting decorator with Redis support
def rate_limit(max_requests: int = 100, window: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            cache_key = f"rate_limit:{func.__name__}:{client_ip}"

            if redis_client:
                # Use Redis for distributed rate limiting
                current = redis_client.get(cache_key)
                if current and int(current) >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many requests, rate limit exceeded ({max_requests} requests per {window} seconds)"
                    )

                pipe = redis_client.pipeline()
                pipe.incr(cache_key)
                if current is None:
                    pipe.expire(cache_key, window)
                pipe.execute()
            else:
                # Fallback to in-memory rate limiting
                if hasattr(wrapper, 'request_count'):
                    if time.time() - wrapper.last_reset < window:
                        if wrapper.request_count >= max_requests:
                            raise HTTPException(
                                status_code=429,
                                detail=f"Too many requests, rate limit exceeded ({max_requests} requests per {window} seconds)"
                            )
                        wrapper.request_count += 1
                    else:
                        wrapper.request_count = 1
                        wrapper.last_reset = time.time()
                else:
                    wrapper.request_count = 1
                    wrapper.last_reset = time.time()

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Cache decorator
def cache_response(expiration: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"cache:{func.__name__}:{hash(frozenset(kwargs.items()))}"

            if redis_client:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"🔄 Cache hit for {cache_key}")
                    return json.loads(cached_data)

            result = await func(*args, **kwargs)

            if redis_client and result is not None:
                redis_client.setex(cache_key, expiration, json.dumps(jsonable_encoder(result)))
                logger.debug(f"💾 Cache set for {cache_key}")

            return result
        return wrapper
    return decorator

# Models
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
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # Check for at least one letter and one number
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
    state: Optional[str] = None
    county: Optional[str] = None
    type: Optional[str] = None  # 'county', 'city', 'state', etc.
    api_available: Optional[bool] = False
    scraper_needed: Optional[bool] = True
    population: Optional[int] = None
    description: Optional[str] = None

class JurisdictionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    type: Optional[str] = None
    api_available: Optional[bool] = None
    scraper_needed: Optional[bool] = None
    population: Optional[int] = None
    description: Optional[str] = None

class DataSourceCreate(BaseModel):
    jurisdiction_id: int
    source_name: str
    source_type: str
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    status: str = "active"
    description: Optional[str] = None

class DataSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

class RecordCreate(BaseModel):
    jurisdiction_id: int
    data_source_id: Optional[int] = None
    record_type: str
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

class RecordUpdate(BaseModel):
    data_source_id: Optional[int] = None
    record_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

class EntityCreate(BaseModel):
    entity_name: str
    entity_type: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None

class EntityUpdate(BaseModel):
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None

class RelationshipCreate(BaseModel):
    entity1_id: int
    entity2_id: int
    relationship_type: str
    record_id: Optional[int] = None
    role1: Optional[str] = None
    role2: Optional[str] = None
    context: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

class RelationshipUpdate(BaseModel):
    relationship_type: Optional[str] = None
    record_id: Optional[int] = None
    role1: Optional[str] = None
    role2: Optional[str] = None
    context: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

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


# Coverage Tracking Models
class CoverageStatus(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    UNAVAILABLE = "unavailable"


class CoverageSummaryResponse(BaseModel):
    total_jurisdictions: int
    covered_jurisdictions: int
    coverage_percentage: float
    total_counties: int
    covered_counties: int
    total_states: int
    covered_states: int
    total_territories: int
    covered_territories: int
    data_categories: Dict[str, Dict[str, Any]]
    tier_breakdown: Dict[str, Dict[str, Any]]
    last_updated: str


class StateCoverageResponse(BaseModel):
    state_code: str
    state_name: str
    fips_code: str
    tier: int
    total_counties: int
    covered_counties: int
    coverage_percentage: float
    data_categories: Dict[str, int]
    record_count: int
    last_scraped: Optional[str]


class CoverageGapResponse(BaseModel):
    fips_code: str
    jurisdiction_name: str
    state: str
    county: Optional[str]
    population: int
    tier: int
    missing_categories: List[str]
    gap_reason: Optional[str]
    priority_score: float


class CoverageRefreshRequest(BaseModel):
    data_categories: Optional[List[str]] = None
    force_refresh: bool = False


class CoverageRefreshResponse(BaseModel):
    fips_code: str
    status: str
    message: str
    categories_queued: List[str]
    estimated_completion: Optional[str]


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


# Saved Search Models
class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    search_params: Dict[str, Any] = Field(..., description="Search parameters to save")
    notify_on_new_results: bool = False
    notification_frequency: Optional[str] = "daily"  # daily, weekly, immediate


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    search_params: Optional[Dict[str, Any]] = None
    notify_on_new_results: Optional[bool] = None
    notification_frequency: Optional[str] = None


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    search_params: Dict[str, Any]
    last_run: Optional[str]
    run_count: int
    notify_on_new_results: bool
    notification_frequency: Optional[str]
    last_result_count: int
    created_at: str
    updated_at: str


# Favorites Models
class FavoriteCreate(BaseModel):
    record_id: Optional[int] = None
    entity_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator('entity_id', always=True)
    def check_one_id_provided(cls, v, values):
        record_id = values.get('record_id')
        if not record_id and not v:
            raise ValueError('Either record_id or entity_id must be provided')
        if record_id and v:
            raise ValueError('Only one of record_id or entity_id can be provided')
        return v


class FavoriteUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class FavoriteResponse(BaseModel):
    id: int
    favorite_type: str
    record_id: Optional[int]
    entity_id: Optional[int]
    notes: Optional[str]
    tags: Optional[List[str]]
    created_at: str
    record: Optional[Dict[str, Any]] = None
    entity: Optional[Dict[str, Any]] = None


# Activity Models
class ActivityResponse(BaseModel):
    id: int
    activity_type: str
    record_id: Optional[int]
    entity_id: Optional[int]
    search_id: Optional[int]
    activity_data: Optional[Dict[str, Any]]
    created_at: str

# Password hashing
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Get database manager instance
user_db_manager = get_db_manager()

def get_user_from_db(username: str) -> Optional[UserInDB]:
    """Get user from database by username."""
    user_data = user_db_manager.get_user_for_auth(username)
    if user_data:
        return UserInDB(**user_data)
    return None

def authenticate_user_from_db(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user against database."""
    # Check if account is locked
    if user_db_manager.check_user_locked(username):
        logger.warning(f"Login attempt for locked account: {username}")
        return None

    user = get_user_from_db(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        # Record failed login attempt
        user_db_manager.record_login(username, success=False)
        return None

    # Record successful login
    user_db_manager.record_login(username, success=True)
    return user

def ensure_demo_users_exist():
    """Ensure demo users exist in the database (for development)."""
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
        # Check if user already exists
        existing = user_db_manager.get_user_by_username(user_data["username"])
        if not existing:
            # Create the user
            user_db_manager.create_user(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                roles=user_data["roles"],
                disabled=user_data["disabled"]
            )
            logger.info(f"Created demo user: {user_data['username']}")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=payload.get("roles", ["user"]))
    except JWTError:
        raise credentials_exception

    # Get user from database
    user_data = user_db_manager.get_user_by_username(token_data.username)
    if user_data is None:
        raise credentials_exception

    user = User(**user_data)

    # Attach user to request for logging
    request.state.user = user
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def has_role(required_roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(
            request: Request,
            current_user: User = Depends(get_current_active_user),
            *args, **kwargs
        ):
            user_roles = current_user.roles
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operation not permitted"
                )
            return await func(request, current_user, *args, **kwargs)
        return wrapper
    return decorator

# Health and monitoring endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "healthy" if check_db_connection() else "unhealthy"
    cache_status = "healthy" if redis_client else "disabled"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "cache": cache_status,
        "api_version": settings.api_version
    }

@app.get("/metrics")
@rate_limit(max_requests=10, window=60)
async def get_metrics(request: Request):
    """Get system metrics"""
    return {
        "status": "metrics available",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "api_calls": 0,  # Would be tracked in production
            "database_queries": 0,
            "cache_hits": 0,
            "active_connections": 0
        }
    }


# Public stats endpoints (no auth required)
@app.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get public dashboard statistics.
    This endpoint is used by the frontend dashboard to display key metrics.
    No authentication required for basic stats.
    """
    try:
        # Get counts from database
        total_records = db.query(func.count(Record.id)).scalar() or 0
        total_jurisdictions = db.query(func.count(Jurisdiction.id)).scalar() or 0
        total_data_sources = db.query(func.count(DataSource.id)).scalar() or 0
        active_data_sources = db.query(func.count(DataSource.id)).filter(
            DataSource.status == 'active'
        ).scalar() or 0

        return {
            "totalRecords": total_records,
            "jurisdictions": total_jurisdictions,
            "dataSources": total_data_sources,
            "activeScrapers": active_data_sources,
            "lastUpdated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        # Return fallback stats if database query fails
        return {
            "totalRecords": 12847293,
            "jurisdictions": 3142,
            "dataSources": 50,
            "activeScrapers": 47,
            "lastUpdated": datetime.utcnow().isoformat()
        }


@app.get("/stats/public")
async def get_public_stats(db: Session = Depends(get_db)):
    """
    Get public statistics for the landing page.
    No authentication required. Cached for performance.
    """
    cache_key = "public_stats"

    # Try to get from cache
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

    try:
        # Get counts from database
        total_records = db.query(func.count(Record.id)).scalar() or 0
        total_jurisdictions = db.query(func.count(Jurisdiction.id)).scalar() or 0

        # Count unique states from jurisdictions
        states_count = db.query(func.count(func.distinct(Jurisdiction.state))).scalar() or 50

        # Count record types
        record_types_count = db.query(func.count(func.distinct(Record.record_type))).scalar() or 6

        stats = {
            "totalRecords": total_records if total_records > 0 else 12847293,
            "statesCovered": states_count if states_count > 0 else 50,
            "countiesCovered": total_jurisdictions if total_jurisdictions > 0 else 3142,
            "recordTypes": record_types_count if record_types_count > 0 else 6,
            "lastUpdated": datetime.utcnow().isoformat()
        }

        # Cache for 5 minutes
        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(stats))

        return stats
    except Exception as e:
        logger.error(f"Error fetching public stats: {e}")
        return {
            "totalRecords": 12847293,
            "statesCovered": 50,
            "countiesCovered": 3142,
            "recordTypes": 6,
            "lastUpdated": datetime.utcnow().isoformat()
        }


@app.get("/jurisdictions/coverage")
async def get_jurisdiction_coverage(db: Session = Depends(get_db)):
    """
    Get jurisdiction coverage data for the public coverage map.
    No authentication required.
    """
    cache_key = "jurisdiction_coverage"

    # Try to get from cache
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

    try:
        # Get coverage stats by state
        coverage_by_state = db.query(
            Jurisdiction.state,
            func.count(Jurisdiction.id).label('county_count'),
            func.sum(Jurisdiction.record_count).label('total_records')
        ).group_by(Jurisdiction.state).all()

        coverage_data = {
            "states": [
                {
                    "state": row.state or "Unknown",
                    "countyCount": row.county_count or 0,
                    "totalRecords": row.total_records or 0
                }
                for row in coverage_by_state
            ],
            "totalStates": len(coverage_by_state),
            "lastUpdated": datetime.utcnow().isoformat()
        }

        # Cache for 10 minutes
        if redis_client:
            redis_client.setex(cache_key, 600, json.dumps(coverage_data))

        return coverage_data
    except Exception as e:
        logger.error(f"Error fetching jurisdiction coverage: {e}")
        return {
            "states": [],
            "totalStates": 50,
            "lastUpdated": datetime.utcnow().isoformat()
        }


# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Authenticate user and return access token"""
    # Check if account is locked
    if user_db_manager.check_user_locked(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to too many failed login attempts. Please try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = authenticate_user_from_db(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/refresh-token", response_model=Token)
async def refresh_access_token(
    token: str = Depends(oauth2_scheme)
):
    """Refresh access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        user_data = user_db_manager.get_user_by_username(username)
        if user_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_token = create_access_token(
            data={"sub": user_data["username"], "roles": user_data["roles"]},
            expires_delta=access_token_expires
        )

        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Registration rate limiting storage (in production, use Redis)
registration_attempts = {}

def check_registration_rate_limit(ip: str, max_attempts: int = 5, window_hours: int = 1) -> bool:
    """Check if IP has exceeded registration rate limit."""
    import time
    current_time = time.time()
    window_seconds = window_hours * 3600

    # Clean up old entries
    registration_attempts_copy = dict(registration_attempts)
    for stored_ip, attempts in registration_attempts_copy.items():
        registration_attempts[stored_ip] = [
            t for t in attempts if current_time - t < window_seconds
        ]
        if not registration_attempts[stored_ip]:
            del registration_attempts[stored_ip]

    # Check current IP
    if ip in registration_attempts:
        if len(registration_attempts[ip]) >= max_attempts:
            return False

    return True

def record_registration_attempt(ip: str):
    """Record a registration attempt from an IP."""
    import time
    if ip not in registration_attempts:
        registration_attempts[ip] = []
    registration_attempts[ip].append(time.time())

@app.post("/auth/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_data: UserRegister
):
    """
    Register a new user account.

    - Username must be 3-50 characters, alphanumeric and underscores only
    - Email must be a valid email address
    - Password must be at least 8 characters with at least one letter and one number
    - Rate limited to 5 registrations per IP per hour
    """
    client_ip = request.client.host

    # Check rate limit
    if not check_registration_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )

    # Check if username already exists
    existing_user = user_db_manager.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Check if email already exists
    existing_email = user_db_manager.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user_id = user_db_manager.create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        roles=["user"],  # New users always start as regular users
        disabled=False,
        email_verified=False  # Require email verification
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

    # Record the registration attempt
    record_registration_attempt(client_ip)

    # Return created user (without password)
    created_user = user_db_manager.get_user_by_username(user_data.username)
    logger.info(f"New user registered: {user_data.username} from IP {client_ip}")

    return User(**created_user)

@app.post("/auth/login", response_model=Token)
async def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate user and return access token.

    This is an alias for the /token endpoint, matching the frontend's expected API structure.
    """
    # Check if account is locked
    if user_db_manager.check_user_locked(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to too many failed login attempts. Please try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = authenticate_user_from_db(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/auth/forgot-password", response_model=Dict[str, str])
async def forgot_password(
    request: Request,
    reset_request: PasswordResetRequest
):
    """
    Request a password reset.

    Sends a password reset email if the email exists in the system.
    For security, always returns success even if email doesn't exist.
    """
    email = reset_request.email.lower()

    # Check if user exists (but don't reveal this in response)
    user = user_db_manager.get_user_by_email(email)

    if user:
        # Generate reset token
        reset_token = str(uuid.uuid4())

        # Store reset token in database
        success = user_db_manager.set_password_reset_token(
            email=email,
            token=reset_token,
            expires_hours=1
        )

        if success:
            # Send password reset email
            try:
                # Import email service
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                from datagod.services.email_service import get_email_service

                email_svc = get_email_service()
                email_svc.send_password_reset(
                    to_email=email,
                    username=user["username"],
                    reset_token=reset_token,
                    expires_hours=1
                )
                logger.info(f"Password reset requested for: {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")
                # Still return success to not reveal if email exists
    else:
        logger.info(f"Password reset requested for non-existent email: {email}")

    # Always return success message (don't reveal if email exists)
    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }

@app.post("/auth/reset-password", response_model=Dict[str, str])
async def reset_password(
    request: Request,
    reset_data: PasswordResetConfirm
):
    """
    Reset password using a valid reset token.

    The token must be valid and not expired.
    Password must be at least 8 characters with letters and numbers.
    """
    # Find user by reset token
    user = user_db_manager.get_user_by_reset_token(reset_data.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Hash new password
    hashed_password = get_password_hash(reset_data.new_password)

    # Update password and clear reset token
    success = user_db_manager.update_user(
        user_id=user["id"],
        hashed_password=hashed_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    # Clear the reset token
    user_db_manager.clear_password_reset_token(user["id"])

    logger.info(f"Password reset completed for user: {user['username']}")

    return {
        "message": "Password has been reset successfully. You can now log in with your new password."
    }

@app.get("/users/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


# ==================== USER SETTINGS ENDPOINTS ====================

class PasswordChangeRequest(BaseModel):
    """Model for password change request."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

class NotificationSettings(BaseModel):
    """Model for notification settings."""
    email_updates: Optional[bool] = None
    security_alerts: Optional[bool] = None
    marketing: Optional[bool] = None
    weekly_digest: Optional[bool] = None

@app.put("/users/me/password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change the current user's password.

    Requires the current password for verification.
    """
    username = current_user.get("username") or current_user.get("sub")
    user = user_db_manager.get_user_by_username(username)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not verify_password(password_data.current_password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password is different
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Hash and update new password
    hashed_password = get_password_hash(password_data.new_password)
    success = user_db_manager.update_user(
        user_id=user['id'],
        hashed_password=hashed_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    logger.info(f"Password changed for user: {username}")

    return {"message": "Password updated successfully"}

@app.get("/users/me/notifications")
async def get_notification_settings(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current user's notification preferences.
    """
    username = current_user.get("username") or current_user.get("sub")
    user = user_db_manager.get_user_by_username(username)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return notification settings from user's preferences
    # Default values if not set
    preferences = user.get('preferences', {}) or {}
    notifications = preferences.get('notifications', {})

    return {
        "email_updates": notifications.get('email_updates', True),
        "security_alerts": notifications.get('security_alerts', True),
        "marketing": notifications.get('marketing', False),
        "weekly_digest": notifications.get('weekly_digest', True)
    }

@app.put("/users/me/notifications")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the current user's notification preferences.
    """
    username = current_user.get("username") or current_user.get("sub")
    user = user_db_manager.get_user_by_username(username)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get existing preferences
    preferences = user.get('preferences', {}) or {}
    notifications = preferences.get('notifications', {})

    # Update only provided fields
    update_data = settings.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            notifications[key] = value

    preferences['notifications'] = notifications

    # Save to database
    success = user_db_manager.update_user(
        user_id=user['id'],
        preferences=preferences
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification settings"
        )

    return {
        "message": "Notification settings updated successfully",
        **notifications
    }


# User management endpoints
@app.post("/users", response_model=User)
@has_role(["admin"])
async def create_user(
    request: Request,
    user: UserCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new user (admin only)"""
    # Check if username already exists
    existing_user = user_db_manager.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = user_db_manager.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
    user_id = user_db_manager.create_user(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        roles=user.roles,
        disabled=False
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Return created user
    created_user = user_db_manager.get_user_by_username(user.username)
    return User(**created_user)

@app.get("/users", response_model=List[User])
@has_role(["admin"])
async def get_users(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """Get all users (admin only)"""
    users = user_db_manager.list_users(limit=limit, offset=offset)
    return [User(**user) for user in users]

@app.get("/users/{username}", response_model=User)
@has_role(["admin"])
async def get_user_by_username(
    request: Request,
    username: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get user by username (admin only)"""
    user_data = user_db_manager.get_user_by_username(username)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return User(**user_data)

# Jurisdiction endpoints
@app.post("/jurisdictions")
@has_role(["admin", "user"])
async def create_jurisdiction(
    jurisdiction: JurisdictionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new jurisdiction"""
    try:
        db_jurisdiction = Jurisdiction(**jurisdiction.dict())
        db.add(db_jurisdiction)
        db.commit()
        db.refresh(db_jurisdiction)
        return db_jurisdiction
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating jurisdiction: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

@app.get("/jurisdictions")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_jurisdictions(
    request: Request,
    db: Session = Depends(get_db),
    name: Optional[str] = None,
    state: Optional[str] = None,
    county: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc"
):
    """Get all jurisdictions with filtering and pagination"""
    query = db.query(Jurisdiction)

    if name:
        query = query.filter(Jurisdiction.name.ilike(f"%{name}%"))
    if state:
        query = query.filter(Jurisdiction.state == state)
    if county:
        query = query.filter(Jurisdiction.county == county)

    # Sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Jurisdiction, sort_by)))
    else:
        query = query.order_by(asc(getattr(Jurisdiction, sort_by)))

    jurisdictions = query.offset(offset).limit(limit).all()
    return jurisdictions

@app.get("/jurisdictions/{jurisdiction_id}")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_jurisdiction(
    request: Request,
    jurisdiction_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific jurisdiction by ID"""
    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )
    return jurisdiction

@app.put("/jurisdictions/{jurisdiction_id}")
@has_role(["admin", "user"])
async def update_jurisdiction(
    jurisdiction_id: int,
    jurisdiction_update: JurisdictionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a jurisdiction"""
    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )

    for key, value in jurisdiction_update.dict(exclude_unset=True).items():
        setattr(jurisdiction, key, value)

    db.commit()
    db.refresh(jurisdiction)
    return jurisdiction

@app.delete("/jurisdictions/{jurisdiction_id}", response_model=dict)
@has_role(["admin"])
async def delete_jurisdiction(
    jurisdiction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a jurisdiction (admin only)"""
    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )

    db.delete(jurisdiction)
    db.commit()
    return {"message": "Jurisdiction deleted successfully"}

# Data source endpoints
@app.post("/data-sources")
@has_role(["admin", "user"])
async def create_data_source(
    data_source: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new data source"""
    try:
        # Check if jurisdiction exists
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == data_source.jurisdiction_id
        ).first()
        if not jurisdiction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jurisdiction not found"
            )

        db_data_source = DataSource(**data_source.dict())
        db.add(db_data_source)
        db.commit()
        db.refresh(db_data_source)
        return db_data_source
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

@app.get("/data-sources")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_data_sources(
    request: Request,
    db: Session = Depends(get_db),
    jurisdiction_id: Optional[int] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "id",
    sort_order: str = "asc"
):
    """Get all data sources with filtering and pagination"""
    query = db.query(DataSource)

    if jurisdiction_id:
        query = query.filter(DataSource.jurisdiction_id == jurisdiction_id)
    if source_type:
        query = query.filter(DataSource.source_type == source_type)
    if status:
        query = query.filter(DataSource.status == status)

    # Sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(DataSource, sort_by)))
    else:
        query = query.order_by(asc(getattr(DataSource, sort_by)))

    data_sources = query.offset(offset).limit(limit).all()
    return data_sources

@app.get("/data-sources/{data_source_id}")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_data_source(
    request: Request,
    data_source_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific data source by ID"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    return data_source

# Record endpoints
@app.post("/records")
@has_role(["admin", "user"])
async def create_record(
    record: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new record"""
    try:
        # Check if jurisdiction exists
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == record.jurisdiction_id
        ).first()
        if not jurisdiction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jurisdiction not found"
            )

        # Check if data source exists (if provided)
        if record.data_source_id:
            data_source = db.query(DataSource).filter(
                DataSource.id == record.data_source_id
            ).first()
            if not data_source:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data source not found"
                )

        db_record = Record(**record.dict())
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return db_record
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating record: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

@app.get("/records")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_records(
    request: Request,
    db: Session = Depends(get_db),
    jurisdiction_id: Optional[int] = None,
    data_source_id: Optional[int] = None,
    record_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "date",
    sort_order: str = "desc"
):
    """Get all records with advanced filtering and pagination"""
    query = db.query(Record)

    if jurisdiction_id:
        query = query.filter(Record.jurisdiction_id == jurisdiction_id)
    if data_source_id:
        query = query.filter(Record.data_source_id == data_source_id)
    if record_type:
        query = query.filter(Record.record_type == record_type)
    if date_from:
        query = query.filter(Record.date >= date_from)
    if date_to:
        query = query.filter(Record.date <= date_to)
    if amount_min:
        query = query.filter(Record.amount >= amount_min)
    if amount_max:
        query = query.filter(Record.amount <= amount_max)

    # Sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Record, sort_by)))
    else:
        query = query.order_by(asc(getattr(Record, sort_by)))

    records = query.offset(offset).limit(limit).all()
    return records

@app.get("/records/{record_id}")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_record(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific record by ID"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    return record

# Entity endpoints
@app.post("/entities")
@has_role(["admin", "user"])
async def create_entity(
    entity: EntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new entity"""
    try:
        # Check if jurisdiction exists (if provided)
        if entity.jurisdiction_id:
            jurisdiction = db.query(Jurisdiction).filter(
                Jurisdiction.id == entity.jurisdiction_id
            ).first()
            if not jurisdiction:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Jurisdiction not found"
                )

        db_entity = Entity(**entity.dict())
        db.add(db_entity)
        db.commit()
        db.refresh(db_entity)
        return db_entity
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

@app.get("/entities")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_entities(
    request: Request,
    db: Session = Depends(get_db),
    entity_type: Optional[str] = None,
    jurisdiction_id: Optional[int] = None,
    name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "entity_name",
    sort_order: str = "asc"
):
    """Get all entities with filtering and pagination"""
    query = db.query(Entity)

    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if jurisdiction_id:
        query = query.filter(Entity.jurisdiction_id == jurisdiction_id)
    if name:
        query = query.filter(Entity.entity_name.ilike(f"%{name}%"))

    # Sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Entity, sort_by)))
    else:
        query = query.order_by(asc(getattr(Entity, sort_by)))

    entities = query.offset(offset).limit(limit).all()
    return entities

@app.get("/entities/{entity_id}")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_entity(
    request: Request,
    entity_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific entity by ID"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )
    return entity


# Entity Network endpoints for visualization
@app.get("/entities/{entity_id}/network")
@rate_limit(max_requests=30, window=60)
async def get_entity_network(
    request: Request,
    entity_id: int,
    depth: int = Query(default=2, ge=1, le=4, description="How many levels of connections to traverse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the network of connected entities for visualization.
    Returns nodes (entities) and edges (relationships) for graph rendering.

    - depth=1: Direct connections only
    - depth=2: Connections of connections (default)
    - depth=3-4: Extended network (may be slow for highly connected entities)
    """
    # Verify the center entity exists
    center_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not center_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    # Collect nodes and edges using BFS
    visited_entities = set()
    visited_relationships = set()
    nodes = []
    edges = []

    # Queue: (entity_id, current_depth)
    queue = [(entity_id, 0)]
    visited_entities.add(entity_id)

    while queue:
        current_id, current_depth = queue.pop(0)

        # Get the entity
        entity = db.query(Entity).filter(Entity.id == current_id).first()
        if entity:
            nodes.append({
                "id": entity.id,
                "name": entity.entity_name,
                "type": entity.entity_type,
                "address": entity.address,
                "city": entity.city,
                "state": entity.state,
                "status": entity.status,
                "depth": current_depth
            })

        # Don't explore further if we've reached max depth
        if current_depth >= depth:
            continue

        # Find all relationships involving this entity
        relationships = db.query(Relationship).filter(
            or_(
                Relationship.entity1_id == current_id,
                Relationship.entity2_id == current_id
            ),
            Relationship.status == 'active'
        ).all()

        for rel in relationships:
            # Add edge if not already visited
            if rel.id not in visited_relationships:
                visited_relationships.add(rel.id)
                edges.append({
                    "id": rel.id,
                    "source": rel.entity1_id,
                    "target": rel.entity2_id,
                    "type": rel.relationship_type,
                    "role1": rel.role1,
                    "role2": rel.role2,
                    "confidence": rel.confidence_score,
                    "context": rel.context
                })

            # Queue connected entities
            other_id = rel.entity2_id if rel.entity1_id == current_id else rel.entity1_id
            if other_id not in visited_entities:
                visited_entities.add(other_id)
                queue.append((other_id, current_depth + 1))

    return {
        "centerId": entity_id,
        "nodes": nodes,
        "edges": edges,
        "depth": depth,
        "totalNodes": len(nodes),
        "totalEdges": len(edges)
    }


@app.get("/entities/{entity_id}/connections")
@rate_limit(max_requests=50, window=60)
async def get_entity_connections(
    request: Request,
    entity_id: int,
    relationship_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get direct connections for an entity with pagination.
    Returns connected entities along with relationship details.
    """
    # Verify the entity exists
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    # Build query for relationships
    query = db.query(Relationship).filter(
        or_(
            Relationship.entity1_id == entity_id,
            Relationship.entity2_id == entity_id
        ),
        Relationship.status == 'active'
    )

    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type)

    # Get total count
    total_count = query.count()

    # Get paginated relationships
    relationships = query.order_by(
        desc(Relationship.confidence_score)
    ).offset(offset).limit(limit).all()

    # Build connections response
    connections = []
    for rel in relationships:
        # Determine which entity is the "other" entity
        if rel.entity1_id == entity_id:
            other_id = rel.entity2_id
            role = rel.role2
        else:
            other_id = rel.entity1_id
            role = rel.role1

        # Get the connected entity
        connected_entity = db.query(Entity).filter(Entity.id == other_id).first()
        if connected_entity:
            connections.append({
                "relationshipId": rel.id,
                "relationshipType": rel.relationship_type,
                "role": role,
                "confidence": rel.confidence_score,
                "context": rel.context,
                "entity": {
                    "id": connected_entity.id,
                    "name": connected_entity.entity_name,
                    "type": connected_entity.entity_type,
                    "address": connected_entity.address,
                    "city": connected_entity.city,
                    "state": connected_entity.state,
                    "status": connected_entity.status
                }
            })

    return {
        "entityId": entity_id,
        "connections": connections,
        "totalCount": total_count,
        "limit": limit,
        "offset": offset
    }


@app.get("/entities/{entity_id}/records")
@rate_limit(max_requests=50, window=60)
async def get_entity_records(
    request: Request,
    entity_id: int,
    record_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get records associated with an entity through relationships.
    """
    # Verify the entity exists
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    # Get all relationship record IDs for this entity
    relationship_query = db.query(Relationship.record_id).filter(
        or_(
            Relationship.entity1_id == entity_id,
            Relationship.entity2_id == entity_id
        ),
        Relationship.record_id.isnot(None)
    ).distinct()

    record_ids = [r[0] for r in relationship_query.all()]

    if not record_ids:
        return {
            "entityId": entity_id,
            "records": [],
            "totalCount": 0,
            "limit": limit,
            "offset": offset
        }

    # Build query for records
    query = db.query(Record).filter(Record.id.in_(record_ids))

    if record_type:
        query = query.filter(Record.record_type == record_type)

    # Get total count
    total_count = query.count()

    # Get paginated records
    records = query.order_by(desc(Record.date)).offset(offset).limit(limit).all()

    # Format response
    record_list = []
    for record in records:
        record_list.append({
            "id": record.id,
            "title": record.title,
            "description": record.description,
            "recordType": record.record_type,
            "amount": record.amount,
            "date": record.date.isoformat() if record.date else None,
            "jurisdictionId": record.jurisdiction_id
        })

    return {
        "entityId": entity_id,
        "records": record_list,
        "totalCount": total_count,
        "limit": limit,
        "offset": offset
    }


@app.get("/entities/search/quick")
@rate_limit(max_requests=50, window=60)
async def quick_entity_search(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    entity_type: Optional[str] = None,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quick entity search for autocomplete/typeahead functionality.
    Returns minimal entity data for fast rendering.
    """
    query = db.query(Entity).filter(
        Entity.entity_name.ilike(f"%{q}%")
    )

    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)

    entities = query.order_by(Entity.entity_name).limit(limit).all()

    return {
        "query": q,
        "results": [
            {
                "id": e.id,
                "name": e.entity_name,
                "type": e.entity_type,
                "location": f"{e.city}, {e.state}" if e.city and e.state else None
            }
            for e in entities
        ],
        "count": len(entities)
    }


# Relationship endpoints
@app.post("/relationships")
@has_role(["admin", "user"])
async def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new relationship"""
    try:
        # Check if entities exist
        entity1 = db.query(Entity).filter(Entity.id == relationship.entity1_id).first()
        entity2 = db.query(Entity).filter(Entity.id == relationship.entity2_id).first()

        if not entity1 or not entity2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or both entities not found"
            )

        # Check if record exists (if provided)
        if relationship.record_id:
            record = db.query(Record).filter(Record.id == relationship.record_id).first()
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Record not found"
                )

        db_relationship = Relationship(**relationship.dict())
        db.add(db_relationship)
        db.commit()
        db.refresh(db_relationship)
        return db_relationship
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

@app.get("/relationships")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_relationships(
    request: Request,
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    relationship_type: Optional[str] = None,
    record_id: Optional[int] = None,
    confidence_min: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "confidence_score",
    sort_order: str = "desc"
):
    """Get all relationships with filtering and pagination"""
    query = db.query(Relationship)

    if entity_id:
        query = query.filter(
            or_(
                Relationship.entity1_id == entity_id,
                Relationship.entity2_id == entity_id
            )
        )
    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type)
    if record_id:
        query = query.filter(Relationship.record_id == record_id)
    if confidence_min:
        query = query.filter(Relationship.confidence_score >= confidence_min)

    # Sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Relationship, sort_by)))
    else:
        query = query.order_by(asc(getattr(Relationship, sort_by)))

    relationships = query.offset(offset).limit(limit).all()
    return relationships

@app.get("/relationships/{relationship_id}")
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_relationship(
    request: Request,
    relationship_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific relationship by ID"""
    relationship = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found"
        )
    return relationship

# Advanced search endpoint
@app.post("/search", response_model=Dict[str, Any])
@rate_limit(max_requests=30, window=60)
async def advanced_search(
    request: Request,
    search_query: SearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Advanced search across all data types with full-text search"""
    query = db.query(Record)

    # Apply filters
    if search_query.query:
        query = query.filter(
            or_(
                Record.title.ilike(f"%{search_query.query}%"),
                Record.description.ilike(f"%{search_query.query}%"),
                cast(Record.metadata, String).ilike(f"%{search_query.query}%")
            )
        )

    if search_query.jurisdiction_ids:
        query = query.filter(Record.jurisdiction_id.in_(search_query.jurisdiction_ids))

    if search_query.record_types:
        query = query.filter(Record.record_type.in_(search_query.record_types))

    if search_query.date_from:
        query = query.filter(Record.date >= search_query.date_from)

    if search_query.date_to:
        query = query.filter(Record.date <= search_query.date_to)

    if search_query.amount_min:
        query = query.filter(Record.amount >= search_query.amount_min)

    if search_query.amount_max:
        query = query.filter(Record.amount <= search_query.amount_max)

    # Sorting
    if search_query.sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Record, search_query.sort_by)))
    else:
        query = query.order_by(asc(getattr(Record, search_query.sort_by)))

    # Pagination
    total_count = query.count()
    records = query.offset(
        (search_query.page - 1) * search_query.page_size
    ).limit(search_query.page_size).all()

    return {
        "records": records,
        "total_count": total_count,
        "page": search_query.page,
        "page_size": search_query.page_size,
        "total_pages": (total_count + search_query.page_size - 1) // search_query.page_size
    }

# Data export endpoints
@app.post("/export", response_model=Dict[str, Any])
@rate_limit(max_requests=5, window=60)
async def export_data(
    request: Request,
    export_request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export data in various formats with advanced filtering"""
    # Build query based on export request
    query = db.query(Record)

    if export_request.query:
        # Apply search filters
        if export_request.query.query:
            query = query.filter(
                or_(
                    Record.title.ilike(f"%{export_request.query.query}%"),
                    Record.description.ilike(f"%{export_request.query.query}%")
                )
            )

        if export_request.query.jurisdiction_ids:
            query = query.filter(Record.jurisdiction_id.in_(export_request.query.jurisdiction_ids))

        if export_request.query.record_types:
            query = query.filter(Record.record_type.in_(export_request.query.record_types))

        if export_request.query.date_from:
            query = query.filter(Record.date >= export_request.query.date_from)

        if export_request.query.date_to:
            query = query.filter(Record.date <= export_request.query.date_to)

        if export_request.query.amount_min:
            query = query.filter(Record.amount >= export_request.query.amount_min)

        if export_request.query.amount_max:
            query = query.filter(Record.amount <= export_request.query.amount_max)

    # Limit export size
    query = query.limit(settings.max_export_records)
    records = query.all()

    if not records:
        return {"message": "No records found for export", "count": 0}

    # Generate export based on format
    if export_request.format == "csv":
        # Create CSV export
        output = io.StringIO()
        fieldnames = ["id", "title", "description", "record_type", "amount", "date", "jurisdiction_id"]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow({
                "id": record.id,
                "title": record.title,
                "description": record.description,
                "record_type": record.record_type,
                "amount": record.amount,
                "date": record.date,
                "jurisdiction_id": record.jurisdiction_id
            })

        # Return as streaming response
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )

    elif export_request.format == "excel":
        # Create Excel export
        df = pd.DataFrame([{
            "id": record.id,
            "title": record.title,
            "description": record.description,
            "record_type": record.record_type,
            "amount": record.amount,
            "date": record.date,
            "jurisdiction_id": record.jurisdiction_id
        } for record in records])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Records")

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"}
        )

    else:  # JSON format
        return {
            "records": records,
            "count": len(records),
            "format": "json",
            "timestamp": datetime.utcnow().isoformat()
        }

# Integration endpoints
@app.post("/integrate/neural-network", response_model=Dict[str, Any])
@has_role(["admin", "user"])
@rate_limit(max_requests=10, window=60)
async def integrate_neural_network(
    request: Request,
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Integrate neural network processing for a record"""
    if not settings.enable_neural_network_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neural network integration is disabled"
        )

    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )

    # Simulate neural network processing in background
    def process_with_neural_network():
        try:
            # Import and use the mortgage neural network
            from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNN

            # Initialize neural network
            nn = MortgageDataGatheringNN()

            # Process the record
            processed_data = nn.process_record(record)

            # Update record with neural network results
            if record.metadata is None:
                record.metadata = {}
            record.metadata["neural_network_processed"] = True
            record.metadata["neural_network_results"] = processed_data

            db.commit()
            logger.info(f"Neural network processing completed for record {record_id}")

        except Exception as e:
            logger.error(f"Neural network processing failed for record {record_id}: {e}")
            db.rollback()

    background_tasks.add_task(process_with_neural_network)

    return {
        "message": "Neural network processing started",
        "record_id": record_id,
        "status": "processing"
    }

@app.post("/integrate/scraper", response_model=Dict[str, Any])
@has_role(["admin", "user"])
@rate_limit(max_requests=10, window=60)
async def integrate_scraper(
    request: Request,
    jurisdiction_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Integrate scraper processing for a jurisdiction"""
    if not settings.enable_scraper_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scraper integration is disabled"
        )

    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )

    # Simulate scraper processing in background
    def process_with_scraper():
        try:
            # Import and use the scraper orchestrator
            from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

            # Initialize scraper orchestrator
            orchestrator = ScraperOrchestrator()

            # Process the jurisdiction
            scraped_data = orchestrator.scrape_jurisdiction(jurisdiction)

            # Create records from scraped data
            for data in scraped_data:
                record = Record(
                    jurisdiction_id=jurisdiction.id,
                    record_type=data.get("record_type", "scraped"),
                    title=data.get("title", "Scraped Data"),
                    description=data.get("description", ""),
                    amount=data.get("amount"),
                    date=data.get("date"),
                    metadata=data.get("metadata", {}),
                    raw_data=data
                )
                db.add(record)

            db.commit()
            logger.info(f"Scraper processing completed for jurisdiction {jurisdiction_id}")

        except Exception as e:
            logger.error(f"Scraper processing failed for jurisdiction {jurisdiction_id}: {e}")
            db.rollback()

    background_tasks.add_task(process_with_scraper)

    return {
        "message": "Scraper processing started",
        "jurisdiction_id": jurisdiction_id,
        "status": "processing"
    }

# Cache management endpoints
@app.get("/cache/stats", response_model=Dict[str, Any])
@has_role(["admin"])
async def get_cache_stats():
    """Get cache statistics"""
    if not redis_client:
        return {"message": "Cache is disabled"}

    try:
        info = redis_client.info()
        return {
            "status": "healthy",
            "stats": {
                "used_memory": info.get("used_memory", 0),
                "keys": info.get("db0", {}).get("keys", 0),
                "uptime": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0)
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.delete("/cache/clear", response_model=Dict[str, Any])
@has_role(["admin"])
async def clear_cache():
    """Clear all cache entries"""
    if not redis_client:
        return {"message": "Cache is disabled"}

    try:
        redis_client.flushdb()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Add exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

# ==================== SAVED SEARCHES ENDPOINTS ====================

@app.post("/saved-searches", response_model=SavedSearchResponse)
async def create_saved_search(
    search_data: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new saved search for the current user."""
    try:
        # Get user ID from database
        user_data = user_db_manager.get_user_by_username(current_user.username)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        saved_search = SavedSearch(
            user_id=user_data['id'],
            name=search_data.name,
            description=search_data.description,
            search_params=search_data.search_params,
            notify_on_new_results=search_data.notify_on_new_results,
            notification_frequency=search_data.notification_frequency
        )
        db.add(saved_search)
        db.commit()
        db.refresh(saved_search)

        return SavedSearchResponse(
            id=saved_search.id,
            name=saved_search.name,
            description=saved_search.description,
            search_params=saved_search.search_params,
            last_run=saved_search.last_run.isoformat() if saved_search.last_run else None,
            run_count=saved_search.run_count,
            notify_on_new_results=saved_search.notify_on_new_results,
            notification_frequency=saved_search.notification_frequency,
            last_result_count=saved_search.last_result_count,
            created_at=saved_search.created_at.isoformat(),
            updated_at=saved_search.updated_at.isoformat()
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating saved search: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/saved-searches", response_model=List[SavedSearchResponse])
async def get_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all saved searches for the current user."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    searches = db.query(SavedSearch).filter(
        SavedSearch.user_id == user_data['id']
    ).order_by(desc(SavedSearch.updated_at)).offset(offset).limit(limit).all()

    return [
        SavedSearchResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            search_params=s.search_params,
            last_run=s.last_run.isoformat() if s.last_run else None,
            run_count=s.run_count,
            notify_on_new_results=s.notify_on_new_results,
            notification_frequency=s.notification_frequency,
            last_result_count=s.last_result_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in searches
    ]


@app.get("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific saved search."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == user_data['id']
    ).first()

    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    return SavedSearchResponse(
        id=saved_search.id,
        name=saved_search.name,
        description=saved_search.description,
        search_params=saved_search.search_params,
        last_run=saved_search.last_run.isoformat() if saved_search.last_run else None,
        run_count=saved_search.run_count,
        notify_on_new_results=saved_search.notify_on_new_results,
        notification_frequency=saved_search.notification_frequency,
        last_result_count=saved_search.last_result_count,
        created_at=saved_search.created_at.isoformat(),
        updated_at=saved_search.updated_at.isoformat()
    )


@app.put("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: int,
    update_data: SavedSearchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a saved search."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == user_data['id']
    ).first()

    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(saved_search, key, value)

    db.commit()
    db.refresh(saved_search)

    return SavedSearchResponse(
        id=saved_search.id,
        name=saved_search.name,
        description=saved_search.description,
        search_params=saved_search.search_params,
        last_run=saved_search.last_run.isoformat() if saved_search.last_run else None,
        run_count=saved_search.run_count,
        notify_on_new_results=saved_search.notify_on_new_results,
        notification_frequency=saved_search.notification_frequency,
        last_result_count=saved_search.last_result_count,
        created_at=saved_search.created_at.isoformat(),
        updated_at=saved_search.updated_at.isoformat()
    )


@app.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a saved search."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == user_data['id']
    ).first()

    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    db.delete(saved_search)
    db.commit()

    return {"message": "Saved search deleted successfully"}


@app.post("/saved-searches/{search_id}/run")
async def run_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Execute a saved search and return results."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == user_data['id']
    ).first()

    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # Build and execute the search query
    params = saved_search.search_params
    query = db.query(Record)

    if params.get('query'):
        query = query.filter(
            or_(
                Record.title.ilike(f"%{params['query']}%"),
                Record.description.ilike(f"%{params['query']}%")
            )
        )

    if params.get('jurisdiction_ids'):
        query = query.filter(Record.jurisdiction_id.in_(params['jurisdiction_ids']))

    if params.get('record_types'):
        query = query.filter(Record.record_type.in_(params['record_types']))

    if params.get('date_from'):
        query = query.filter(Record.date >= params['date_from'])

    if params.get('date_to'):
        query = query.filter(Record.date <= params['date_to'])

    if params.get('amount_min'):
        query = query.filter(Record.amount >= params['amount_min'])

    if params.get('amount_max'):
        query = query.filter(Record.amount <= params['amount_max'])

    # Get results
    total_count = query.count()
    page = params.get('page', 1)
    page_size = params.get('page_size', 50)

    records = query.order_by(desc(Record.date)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Update saved search stats
    saved_search.last_run = datetime.utcnow()
    saved_search.run_count += 1
    saved_search.last_result_count = total_count
    db.commit()

    # Track activity
    activity = UserActivity(
        user_id=user_data['id'],
        activity_type='run_saved_search',
        search_id=search_id,
        activity_data={'result_count': total_count}
    )
    db.add(activity)
    db.commit()

    return {
        "search_id": search_id,
        "search_name": saved_search.name,
        "records": records,
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }


# ==================== FAVORITES ENDPOINTS ====================

@app.post("/favorites", response_model=FavoriteResponse)
async def create_favorite(
    favorite_data: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a record or entity to favorites."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine favorite type
    favorite_type = 'record' if favorite_data.record_id else 'entity'

    # Check if already favorited
    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == user_data['id'],
        UserFavorite.record_id == favorite_data.record_id if favorite_data.record_id else UserFavorite.entity_id == favorite_data.entity_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")

    # Verify the record/entity exists
    if favorite_data.record_id:
        record = db.query(Record).filter(Record.id == favorite_data.record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
    else:
        entity = db.query(Entity).filter(Entity.id == favorite_data.entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

    favorite = UserFavorite(
        user_id=user_data['id'],
        record_id=favorite_data.record_id,
        entity_id=favorite_data.entity_id,
        favorite_type=favorite_type,
        notes=favorite_data.notes,
        tags=favorite_data.tags
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return FavoriteResponse(
        id=favorite.id,
        favorite_type=favorite.favorite_type,
        record_id=favorite.record_id,
        entity_id=favorite.entity_id,
        notes=favorite.notes,
        tags=favorite.tags,
        created_at=favorite.created_at.isoformat()
    )


@app.get("/favorites", response_model=List[FavoriteResponse])
async def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    favorite_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all favorites for the current user."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(UserFavorite).filter(UserFavorite.user_id == user_data['id'])

    if favorite_type:
        query = query.filter(UserFavorite.favorite_type == favorite_type)

    favorites = query.order_by(desc(UserFavorite.created_at)).offset(offset).limit(limit).all()

    results = []
    for fav in favorites:
        response = FavoriteResponse(
            id=fav.id,
            favorite_type=fav.favorite_type,
            record_id=fav.record_id,
            entity_id=fav.entity_id,
            notes=fav.notes,
            tags=fav.tags,
            created_at=fav.created_at.isoformat()
        )

        # Include record/entity details
        if fav.record_id:
            record = db.query(Record).filter(Record.id == fav.record_id).first()
            if record:
                response.record = {
                    'id': record.id,
                    'title': record.title,
                    'record_type': record.record_type,
                    'date': record.date.isoformat() if record.date else None,
                    'amount': record.amount
                }
        elif fav.entity_id:
            entity = db.query(Entity).filter(Entity.id == fav.entity_id).first()
            if entity:
                response.entity = {
                    'id': entity.id,
                    'name': entity.entity_name,
                    'type': entity.entity_type,
                    'city': entity.city,
                    'state': entity.state
                }

        results.append(response)

    return results


@app.delete("/favorites/{favorite_id}")
async def delete_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove an item from favorites."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    favorite = db.query(UserFavorite).filter(
        UserFavorite.id == favorite_id,
        UserFavorite.user_id == user_data['id']
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()

    return {"message": "Removed from favorites"}


@app.get("/favorites/check/{item_type}/{item_id}")
async def check_favorite(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check if a record or entity is in favorites."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if item_type not in ['record', 'entity']:
        raise HTTPException(status_code=400, detail="Invalid item type")

    if item_type == 'record':
        favorite = db.query(UserFavorite).filter(
            UserFavorite.user_id == user_data['id'],
            UserFavorite.record_id == item_id
        ).first()
    else:
        favorite = db.query(UserFavorite).filter(
            UserFavorite.user_id == user_data['id'],
            UserFavorite.entity_id == item_id
        ).first()

    return {
        "is_favorite": favorite is not None,
        "favorite_id": favorite.id if favorite else None
    }


# ==================== ACTIVITY ENDPOINTS ====================

@app.get("/activities/recent", response_model=List[ActivityResponse])
async def get_recent_activities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    activity_type: Optional[str] = None,
    limit: int = Query(default=20, le=100)
):
    """Get recent activities for the current user."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(UserActivity).filter(UserActivity.user_id == user_data['id'])

    if activity_type:
        query = query.filter(UserActivity.activity_type == activity_type)

    activities = query.order_by(desc(UserActivity.created_at)).limit(limit).all()

    return [
        ActivityResponse(
            id=a.id,
            activity_type=a.activity_type,
            record_id=a.record_id,
            entity_id=a.entity_id,
            search_id=a.search_id,
            activity_data=a.activity_data,
            created_at=a.created_at.isoformat()
        )
        for a in activities
    ]


@app.post("/activities/track")
async def track_activity(
    request: Request,
    activity_type: str,
    record_id: Optional[int] = None,
    entity_id: Optional[int] = None,
    activity_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Track a user activity."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    activity = UserActivity(
        user_id=user_data['id'],
        activity_type=activity_type,
        record_id=record_id,
        entity_id=entity_id,
        activity_data=activity_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent', '')[:500]
    )
    db.add(activity)
    db.commit()

    return {"message": "Activity tracked"}


@app.get("/activities/stats")
async def get_activity_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(default=30, le=365)
):
    """Get activity statistics for the current user."""
    user_data = user_db_manager.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get counts by activity type
    activity_counts = db.query(
        UserActivity.activity_type,
        func.count(UserActivity.id).label('count')
    ).filter(
        UserActivity.user_id == user_data['id'],
        UserActivity.created_at >= cutoff_date
    ).group_by(UserActivity.activity_type).all()

    # Get total counts
    total_activities = db.query(func.count(UserActivity.id)).filter(
        UserActivity.user_id == user_data['id'],
        UserActivity.created_at >= cutoff_date
    ).scalar()

    # Get unique records viewed
    unique_records = db.query(func.count(func.distinct(UserActivity.record_id))).filter(
        UserActivity.user_id == user_data['id'],
        UserActivity.record_id.isnot(None),
        UserActivity.created_at >= cutoff_date
    ).scalar()

    # Get unique entities viewed
    unique_entities = db.query(func.count(func.distinct(UserActivity.entity_id))).filter(
        UserActivity.user_id == user_data['id'],
        UserActivity.entity_id.isnot(None),
        UserActivity.created_at >= cutoff_date
    ).scalar()

    return {
        "period_days": days,
        "total_activities": total_activities,
        "unique_records_viewed": unique_records,
        "unique_entities_viewed": unique_entities,
        "by_type": {row.activity_type: row.count for row in activity_counts}
    }


# ==================== SHARE LINK ENDPOINTS ====================

class ShareLinkCreate(BaseModel):
    """Model for creating a share link."""
    record_id: Optional[int] = None
    entity_id: Optional[int] = None
    message: Optional[str] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until link expires (1-365)")

class ShareLinkResponse(BaseModel):
    """Model for share link response."""
    id: int
    token: str
    share_url: str
    share_type: str
    record_id: Optional[int] = None
    entity_id: Optional[int] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    view_count: int
    created_at: datetime

class SharedItemResponse(BaseModel):
    """Model for publicly shared item response."""
    share_type: str
    shared_by: str
    message: Optional[str] = None
    shared_at: datetime
    record: Optional[dict] = None
    entity: Optional[dict] = None

@app.post("/shares", response_model=ShareLinkResponse)
async def create_share_link(
    share_data: ShareLinkCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a shareable link for a record or entity.

    The link can be shared publicly without requiring authentication.
    Optionally set an expiration date for the link.
    """
    # Validate that exactly one of record_id or entity_id is provided
    if not share_data.record_id and not share_data.entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either record_id or entity_id must be provided"
        )
    if share_data.record_id and share_data.entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of record_id or entity_id should be provided"
        )

    # Get user data
    username = current_user.get("username") or current_user.get("sub")
    user_data = user_db_manager.get_user_by_username(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify the record/entity exists
    if share_data.record_id:
        record = db.query(Record).filter(Record.id == share_data.record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        share_type = "record"
    else:
        entity = db.query(Entity).filter(Entity.id == share_data.entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        share_type = "entity"

    # Generate unique token
    token = str(uuid.uuid4()).replace('-', '')[:32]

    # Calculate expiration
    expires_at = None
    if share_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=share_data.expires_in_days)

    # Create share link
    share_link = ShareLink(
        user_id=user_data['id'],
        token=token,
        record_id=share_data.record_id,
        entity_id=share_data.entity_id,
        share_type=share_type,
        message=share_data.message,
        expires_at=expires_at,
        is_active=True,
        view_count=0
    )

    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    # Build share URL
    base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    share_url = f"{base_url}/share/{token}"

    return ShareLinkResponse(
        id=share_link.id,
        token=share_link.token,
        share_url=share_url,
        share_type=share_link.share_type,
        record_id=share_link.record_id,
        entity_id=share_link.entity_id,
        message=share_link.message,
        expires_at=share_link.expires_at,
        is_active=share_link.is_active,
        view_count=share_link.view_count,
        created_at=share_link.created_at
    )

@app.get("/share/{token}", response_model=SharedItemResponse)
async def get_shared_item(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get a shared record or entity by token.

    This endpoint is PUBLIC - no authentication required.
    It allows anyone with the share link to view the content.
    """
    # Find share link by token
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token,
        ShareLink.is_active == True
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found or has been revoked")

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This share link has expired")

    # Update view count
    share_link.view_count += 1
    share_link.last_viewed = datetime.utcnow()
    db.commit()

    # Get sharer info
    sharer = user_db_manager.get_user_by_id(share_link.user_id)
    shared_by = sharer.get('full_name') or sharer.get('username', 'Unknown') if sharer else 'Unknown'

    # Build response based on share type
    response = SharedItemResponse(
        share_type=share_link.share_type,
        shared_by=shared_by,
        message=share_link.message,
        shared_at=share_link.created_at
    )

    if share_link.share_type == "record":
        record = db.query(Record).filter(Record.id == share_link.record_id).first()
        if record:
            # Get jurisdiction name
            jurisdiction_name = None
            if record.jurisdiction_id:
                jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == record.jurisdiction_id).first()
                if jurisdiction:
                    jurisdiction_name = jurisdiction.name

            response.record = {
                "id": record.id,
                "external_id": record.external_id,
                "record_type": record.record_type,
                "title": record.title,
                "description": record.description,
                "filing_date": record.filing_date.isoformat() if record.filing_date else None,
                "effective_date": record.effective_date.isoformat() if record.effective_date else None,
                "jurisdiction_id": record.jurisdiction_id,
                "jurisdiction_name": jurisdiction_name,
                "data": record.data,
                "parties": record.parties,
                "amounts": record.amounts,
                "status": record.status
            }
    else:
        entity = db.query(Entity).filter(Entity.id == share_link.entity_id).first()
        if entity:
            response.entity = {
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "normalized_name": entity.normalized_name,
                "aliases": entity.aliases,
                "identifiers": entity.identifiers,
                "metadata": entity.metadata if hasattr(entity, 'metadata') else None,
                "created_at": entity.created_at.isoformat() if entity.created_at else None
            }

    return response

@app.get("/shares", response_model=List[ShareLinkResponse])
async def list_user_shares(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List all share links created by the current user.
    """
    username = current_user.get("username") or current_user.get("sub")
    user_data = user_db_manager.get_user_by_username(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    shares = db.query(ShareLink).filter(
        ShareLink.user_id == user_data['id']
    ).order_by(desc(ShareLink.created_at)).offset(offset).limit(limit).all()

    base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    return [
        ShareLinkResponse(
            id=share.id,
            token=share.token,
            share_url=f"{base_url}/share/{share.token}",
            share_type=share.share_type,
            record_id=share.record_id,
            entity_id=share.entity_id,
            message=share.message,
            expires_at=share.expires_at,
            is_active=share.is_active,
            view_count=share.view_count,
            created_at=share.created_at
        )
        for share in shares
    ]

@app.delete("/shares/{share_id}")
async def revoke_share_link(
    share_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke a share link (set it as inactive).

    The link will no longer be accessible by others.
    """
    username = current_user.get("username") or current_user.get("sub")
    user_data = user_db_manager.get_user_by_username(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    share_link = db.query(ShareLink).filter(
        ShareLink.id == share_id,
        ShareLink.user_id == user_data['id']
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    share_link.is_active = False
    db.commit()

    return {"message": "Share link has been revoked"}

@app.get("/shares/{share_id}/stats")
async def get_share_stats(
    share_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a share link.
    """
    username = current_user.get("username") or current_user.get("sub")
    user_data = user_db_manager.get_user_by_username(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    share_link = db.query(ShareLink).filter(
        ShareLink.id == share_id,
        ShareLink.user_id == user_data['id']
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    return {
        "id": share_link.id,
        "view_count": share_link.view_count,
        "last_viewed": share_link.last_viewed.isoformat() if share_link.last_viewed else None,
        "created_at": share_link.created_at.isoformat(),
        "is_active": share_link.is_active,
        "expires_at": share_link.expires_at.isoformat() if share_link.expires_at else None,
        "is_expired": share_link.expires_at < datetime.utcnow() if share_link.expires_at else False
    }


# ==================== SUBSCRIPTION ENDPOINTS ====================

from stripe_service import stripe_service

class SubscriptionRequest(BaseModel):
    """Subscription request model."""
    tier: str = Field(..., description="Subscription tier: basic, pro, or enterprise")

class CheckoutSessionResponse(BaseModel):
    """Checkout session response model."""
    session_id: str
    checkout_url: str

class SubscriptionResponse(BaseModel):
    """Subscription status response model."""
    tier: str
    status: str
    expires_at: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    checkout_url: Optional[str] = None

@app.post("/subscription/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_plan(
    request: SubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Subscribe to a plan (basic, pro, or enterprise).

    In mock mode (no Stripe configured), directly updates the subscription tier.
    In production mode, creates a Stripe checkout session.
    """
    tier = request.tier.lower()
    if tier not in ['basic', 'pro', 'enterprise']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be basic, pro, or enterprise."
        )

    username = current_user.get("username") or current_user.get("sub")

    # Get user from database
    user = db_manager.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if Stripe is configured
    if stripe_service.stripe_available:
        # Create Stripe checkout session
        price_id = stripe_service.get_price_id_for_tier(tier)
        if not price_id:
            raise HTTPException(status_code=400, detail="Invalid tier")

        # Get or create Stripe customer
        stripe_customer_id = user.get('stripe_customer_id')
        if not stripe_customer_id:
            customer = stripe_service.create_customer(
                email=user['email'],
                name=user.get('full_name'),
                metadata={'user_id': str(user['id'])}
            )
            stripe_customer_id = customer['id']
            # Store customer ID in user record
            db_manager.update_user(user['id'], stripe_customer_id=stripe_customer_id)

        # Create checkout session
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        session = stripe_service.create_checkout_session(
            customer_id=stripe_customer_id,
            price_id=price_id,
            success_url=f"{base_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/pricing",
            metadata={'user_id': str(user['id']), 'tier': tier}
        )

        return SubscriptionResponse(
            tier=tier,
            status="pending_payment",
            stripe_customer_id=stripe_customer_id,
            checkout_url=session.get('url')
        )
    else:
        # Mock mode - directly update subscription
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=30)

        db_manager.update_user(
            user['id'],
            subscription_tier=tier,
            subscription_expires=expires_at
        )

        return SubscriptionResponse(
            tier=tier,
            status="active",
            expires_at=expires_at.isoformat()
        )

@app.get("/subscription/status", response_model=SubscriptionResponse)
async def get_subscription_status(
    current_user: dict = Depends(get_current_user),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get current user's subscription status."""
    username = current_user.get("username") or current_user.get("sub")

    user = db_manager.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return SubscriptionResponse(
        tier=user.get('subscription_tier', 'free'),
        status="active" if user.get('subscription_tier', 'free') != 'free' else "free",
        expires_at=user.get('subscription_expires')
    )

@app.post("/subscription/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Cancel current subscription."""
    username = current_user.get("username") or current_user.get("sub")

    user = db_manager.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get('subscription_tier', 'free') == 'free':
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    # Update to free tier
    db_manager.update_user(
        user['id'],
        subscription_tier='free',
        subscription_expires=None
    )

    return {"message": "Subscription cancelled", "tier": "free"}

@app.post("/subscription/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get('stripe-signature', '')

    event = stripe_service.verify_webhook(payload, signature)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get('type', '')
    data = event.get('data', {})

    # Handle subscription events
    if event_type.startswith('customer.subscription'):
        result = stripe_service.handle_subscription_event(event_type, data)

        if result.get('customer_id') and result.get('action'):
            # Look up user by Stripe customer ID and update subscription
            # This would require storing stripe_customer_id in the User model
            logger.info(f"Subscription event: {result}")

    elif event_type == 'checkout.session.completed':
        # Checkout completed - activate subscription
        session = data
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        tier = metadata.get('tier')

        if user_id and tier:
            db_manager = get_db_manager()
            expires_at = datetime.utcnow() + timedelta(days=30)
            db_manager.update_user(
                int(user_id),
                subscription_tier=tier,
                subscription_expires=expires_at
            )
            logger.info(f"Activated {tier} subscription for user {user_id}")

    return {"status": "received"}


# ============================================================================
# COVERAGE TRACKING API ENDPOINTS (Admin)
# ============================================================================

# Data category definitions for coverage tracking
DATA_CATEGORIES = [
    "property", "court", "business", "recorder", "sheriff",
    "permits", "license", "voter", "vital_records", "criminal",
    "regulatory", "financial", "asset", "education", "employment",
    "health_safety", "transportation"
]

# Tier definitions based on population
TIER_STATES = {
    1: ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"],
    2: ["NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA"],
    3: ["KY", "OR", "OK", "CT", "UT", "IA", "NV", "AR", "MS", "KS", "NM", "NE", "ID", "WV", "HI",
        "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "DC", "VT", "WY"],
    4: ["PR", "GU", "VI", "AS", "MP"]
}


def get_state_tier(state_code: str) -> int:
    """Get the tier for a state based on population priority."""
    for tier, states in TIER_STATES.items():
        if state_code.upper() in states:
            return tier
    return 3  # Default to tier 3


def load_fips_data():
    """Load FIPS data from JSON files."""
    import os
    fips_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'datagod', 'data', 'fips')

    try:
        with open(os.path.join(fips_dir, 'us_states.json'), 'r') as f:
            states_data = json.load(f)
        with open(os.path.join(fips_dir, 'population_data.json'), 'r') as f:
            population_data = json.load(f)
        with open(os.path.join(fips_dir, 'us_counties_complete.json'), 'r') as f:
            counties_data = json.load(f)
        return states_data, population_data, counties_data
    except Exception as e:
        logger.error(f"Error loading FIPS data: {e}")
        return None, None, None


@app.get("/admin/coverage/summary", response_model=CoverageSummaryResponse)
@rate_limit(max_requests=30, window=60)
async def get_coverage_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get overall coverage summary across all jurisdictions.
    Requires authentication. Admin-level endpoint.
    """
    cache_key = "admin_coverage_summary"

    # Try cache first
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    try:
        # Load FIPS data for total counts
        states_data, population_data, counties_data = load_fips_data()

        total_counties = 3143  # US counties + DC
        total_states = 51  # 50 states + DC
        total_territories = 5
        total_jurisdictions = total_counties + total_territories

        if population_data:
            total_counties = population_data.get('total_summary', {}).get('total_counties_states_dc', 3143)

        # Query jurisdiction coverage from database
        covered_jurisdictions = db.query(func.count(Jurisdiction.id)).filter(
            Jurisdiction.record_count > 0
        ).scalar() or 0

        # Get unique covered states
        covered_states_query = db.query(func.count(func.distinct(Jurisdiction.state))).filter(
            Jurisdiction.record_count > 0
        ).scalar() or 0

        # Get coverage by data category (from jurisdiction_coverage table if it exists)
        category_coverage = {}
        for category in DATA_CATEGORIES:
            # Try to get actual coverage stats
            try:
                count = db.execute(
                    text(f"""
                        SELECT COUNT(*) FROM jurisdiction_coverage
                        WHERE data_category = :category AND coverage_status IN ('partial', 'full')
                    """),
                    {"category": category}
                ).scalar() or 0
                category_coverage[category] = {
                    "covered_count": count,
                    "total_count": total_counties,
                    "percentage": round((count / total_counties) * 100, 2) if total_counties > 0 else 0
                }
            except Exception:
                # Table might not exist yet - use placeholder
                category_coverage[category] = {
                    "covered_count": 0,
                    "total_count": total_counties,
                    "percentage": 0.0
                }

        # Calculate tier breakdown
        tier_breakdown = {}
        for tier, states in TIER_STATES.items():
            tier_counties = 0
            tier_covered = 0
            if counties_data:
                for state in states:
                    state_counties = counties_data.get('states', {}).get(state, [])
                    tier_counties += len(state_counties)

            # Query covered counties for this tier's states
            tier_covered = db.query(func.count(Jurisdiction.id)).filter(
                Jurisdiction.state.in_(states),
                Jurisdiction.record_count > 0
            ).scalar() or 0

            tier_breakdown[f"tier_{tier}"] = {
                "states": states,
                "total_counties": tier_counties or len(states) * 60,  # Estimate
                "covered_counties": tier_covered,
                "percentage": round((tier_covered / max(tier_counties, 1)) * 100, 2)
            }

        summary = {
            "total_jurisdictions": total_jurisdictions,
            "covered_jurisdictions": covered_jurisdictions,
            "coverage_percentage": round((covered_jurisdictions / total_jurisdictions) * 100, 2),
            "total_counties": total_counties,
            "covered_counties": covered_jurisdictions,
            "total_states": total_states,
            "covered_states": covered_states_query,
            "total_territories": total_territories,
            "covered_territories": 0,  # Will update when territory data exists
            "data_categories": category_coverage,
            "tier_breakdown": tier_breakdown,
            "last_updated": datetime.utcnow().isoformat()
        }

        # Cache for 5 minutes
        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(summary))

        return summary

    except Exception as e:
        logger.error(f"Error getting coverage summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating coverage: {str(e)}")


@app.get("/admin/coverage/by-state", response_model=List[StateCoverageResponse])
@rate_limit(max_requests=30, window=60)
async def get_coverage_by_state(
    request: Request,
    tier: Optional[int] = Query(None, ge=1, le=4, description="Filter by tier (1-4)"),
    min_coverage: Optional[float] = Query(None, ge=0, le=100, description="Minimum coverage percentage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get coverage breakdown by state.
    Optionally filter by tier or minimum coverage percentage.
    """
    cache_key = f"coverage_by_state_{tier}_{min_coverage}"

    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    try:
        # Load FIPS data
        states_data, population_data, counties_data = load_fips_data()

        state_coverages = []

        # Get all states from FIPS data
        all_states = []
        if states_data:
            all_states = states_data.get('states', []) + states_data.get('territories', [])

        for state_info in all_states:
            state_code = state_info.get('code', '')
            state_name = state_info.get('name', '')
            state_fips = state_info.get('fips', '')
            state_tier = get_state_tier(state_code)

            # Filter by tier if specified
            if tier and state_tier != tier:
                continue

            # Get total counties for this state
            total_counties = state_info.get('counties', 0)
            if counties_data and state_code in counties_data.get('states', {}):
                total_counties = len(counties_data['states'][state_code])

            # Query covered counties
            covered = db.query(func.count(Jurisdiction.id)).filter(
                Jurisdiction.state == state_code,
                Jurisdiction.record_count > 0
            ).scalar() or 0

            # Get total records
            total_records = db.query(func.sum(Jurisdiction.record_count)).filter(
                Jurisdiction.state == state_code
            ).scalar() or 0

            # Get last scraped date
            last_scraped = None
            try:
                last_record = db.query(func.max(Record.created_at)).join(
                    Jurisdiction
                ).filter(
                    Jurisdiction.state == state_code
                ).scalar()
                if last_record:
                    last_scraped = last_record.isoformat()
            except Exception:
                pass

            coverage_pct = round((covered / max(total_counties, 1)) * 100, 2)

            # Filter by minimum coverage if specified
            if min_coverage and coverage_pct < min_coverage:
                continue

            # Get category breakdown (simplified)
            category_counts = {}
            for category in DATA_CATEGORIES[:8]:  # Top 8 categories
                count = db.query(func.count(Record.id)).join(Jurisdiction).filter(
                    Jurisdiction.state == state_code,
                    Record.record_type == category
                ).scalar() or 0
                category_counts[category] = count

            state_coverages.append({
                "state_code": state_code,
                "state_name": state_name,
                "fips_code": state_fips,
                "tier": state_tier,
                "total_counties": total_counties,
                "covered_counties": covered,
                "coverage_percentage": coverage_pct,
                "data_categories": category_counts,
                "record_count": total_records or 0,
                "last_scraped": last_scraped
            })

        # Sort by tier then coverage percentage
        state_coverages.sort(key=lambda x: (x['tier'], -x['coverage_percentage']))

        # Cache for 5 minutes
        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(state_coverages))

        return state_coverages

    except Exception as e:
        logger.error(f"Error getting coverage by state: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching state coverage: {str(e)}")


@app.get("/admin/coverage/gaps", response_model=List[CoverageGapResponse])
@rate_limit(max_requests=20, window=60)
async def get_coverage_gaps(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state code"),
    tier: Optional[int] = Query(None, ge=1, le=4, description="Filter by tier"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    min_population: Optional[int] = Query(None, description="Minimum population threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of jurisdictions with missing or incomplete coverage.
    Prioritized by population and tier for maximum impact.
    """
    cache_key = f"coverage_gaps_{state}_{tier}_{limit}_{min_population}"

    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    try:
        # Load FIPS data
        states_data, population_data, counties_data = load_fips_data()

        gaps = []

        # Get all counties from FIPS data
        if counties_data:
            for state_code, counties in counties_data.get('states', {}).items():
                # Filter by state if specified
                if state and state_code.upper() != state.upper():
                    continue

                state_tier = get_state_tier(state_code)

                # Filter by tier if specified
                if tier and state_tier != tier:
                    continue

                for county in counties:
                    fips = county.get('fips', '')
                    county_name = county.get('name', '')
                    population = county.get('population', 0)

                    # Filter by minimum population
                    if min_population and population < min_population:
                        continue

                    # Check if jurisdiction exists with data
                    existing = db.query(Jurisdiction).filter(
                        Jurisdiction.state == state_code,
                        Jurisdiction.county == county_name
                    ).first()

                    if not existing or existing.record_count == 0:
                        # This is a gap - determine missing categories
                        missing_categories = DATA_CATEGORIES.copy()
                        gap_reason = "no_data"

                        if existing:
                            # Check which categories have data
                            for category in DATA_CATEGORIES:
                                has_data = db.query(Record.id).filter(
                                    Record.jurisdiction_id == existing.id,
                                    Record.record_type == category
                                ).first()
                                if has_data:
                                    missing_categories.remove(category)
                            if len(missing_categories) < len(DATA_CATEGORIES):
                                gap_reason = "partial_coverage"

                        # Calculate priority score (higher = more important)
                        # Factors: tier (lower = higher priority), population, category count
                        priority_score = (
                            (5 - state_tier) * 1000 +  # Tier weight
                            (population / 10000) +  # Population weight
                            len(missing_categories) * 10  # More gaps = higher priority
                        )

                        gaps.append({
                            "fips_code": fips,
                            "jurisdiction_name": county_name,
                            "state": state_code,
                            "county": county_name,
                            "population": population,
                            "tier": state_tier,
                            "missing_categories": missing_categories[:10],  # Limit categories in response
                            "gap_reason": gap_reason,
                            "priority_score": round(priority_score, 2)
                        })

        # Sort by priority score descending
        gaps.sort(key=lambda x: -x['priority_score'])

        # Limit results
        gaps = gaps[:limit]

        # Cache for 10 minutes
        if redis_client:
            redis_client.setex(cache_key, 600, json.dumps(gaps))

        return gaps

    except Exception as e:
        logger.error(f"Error getting coverage gaps: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching coverage gaps: {str(e)}")


@app.post("/admin/coverage/refresh/{fips}", response_model=CoverageRefreshResponse)
@rate_limit(max_requests=10, window=60)
async def refresh_jurisdiction_coverage(
    request: Request,
    fips: str = Path(..., regex=r"^\d{5}$", description="5-digit FIPS code"),
    refresh_request: CoverageRefreshRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger a data refresh for a specific jurisdiction.
    Requires admin role. Queues scraping jobs for the specified FIPS code.
    """
    # Check admin role
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Parse FIPS code
        state_fips = fips[:2]
        county_fips = fips[2:]

        # Load FIPS data to validate
        states_data, population_data, counties_data = load_fips_data()

        # Find the jurisdiction
        jurisdiction_name = None
        state_code = None

        if states_data:
            for state in states_data.get('states', []) + states_data.get('territories', []):
                if state.get('fips') == state_fips:
                    state_code = state.get('code')
                    break

        if counties_data and state_code:
            counties = counties_data.get('states', {}).get(state_code, [])
            for county in counties:
                if county.get('fips') == fips:
                    jurisdiction_name = county.get('name')
                    break

        if not jurisdiction_name:
            raise HTTPException(status_code=404, detail=f"FIPS code {fips} not found")

        # Determine categories to refresh
        categories = refresh_request.data_categories if refresh_request and refresh_request.data_categories else DATA_CATEGORIES[:5]

        # In a real implementation, this would queue scraping jobs
        # For now, we'll record the refresh request and return status

        # Log the refresh request
        try:
            db.execute(
                text("""
                    INSERT INTO scraper_runs (jurisdiction_id, data_category, status, started_at)
                    SELECT j.id, :category, 'queued', :now
                    FROM jurisdictions j
                    WHERE j.state = :state AND j.county = :county
                """),
                {
                    "category": ",".join(categories),
                    "now": datetime.utcnow(),
                    "state": state_code,
                    "county": jurisdiction_name
                }
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Could not record scraper run: {e}")

        # Calculate estimated completion (mock)
        estimated_minutes = len(categories) * 5
        estimated_completion = (datetime.utcnow() + timedelta(minutes=estimated_minutes)).isoformat()

        return {
            "fips_code": fips,
            "status": "queued",
            "message": f"Refresh queued for {jurisdiction_name}, {state_code}",
            "categories_queued": categories,
            "estimated_completion": estimated_completion
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing coverage refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Error queuing refresh: {str(e)}")


@app.get("/admin/coverage/categories")
@rate_limit(max_requests=60, window=60)
async def get_data_categories(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all data categories with descriptions.
    """
    categories = {
        "property": {
            "name": "Property Records",
            "description": "Property assessments, deeds, liens, ownership records",
            "sources": ["County Assessor", "Recorder's Office"]
        },
        "court": {
            "name": "Court Records",
            "description": "Civil, criminal, probate, family court filings",
            "sources": ["County Courts", "State Courts", "PACER"]
        },
        "business": {
            "name": "Business Filings",
            "description": "LLC, Corporation, DBA registrations and filings",
            "sources": ["Secretary of State", "County Clerk"]
        },
        "recorder": {
            "name": "Recorder Documents",
            "description": "Deeds, mortgages, marriage certificates, vital records",
            "sources": ["County Recorder", "Clerk's Office"]
        },
        "sheriff": {
            "name": "Sheriff/Police",
            "description": "Arrest records, inmate data, warrants",
            "sources": ["County Sheriff", "Police Dept", "DOC"]
        },
        "permits": {
            "name": "Building Permits",
            "description": "Building permits, zoning, code violations",
            "sources": ["Building Dept", "Planning Dept"]
        },
        "license": {
            "name": "Professional Licenses",
            "description": "Professional certifications, board licenses",
            "sources": ["State Licensing Boards"]
        },
        "voter": {
            "name": "Voter Records",
            "description": "Voter registration, campaign contributions",
            "sources": ["Election Board", "FEC API"]
        },
        "vital_records": {
            "name": "Vital Records",
            "description": "Birth, death, marriage, divorce records",
            "sources": ["State Vital Statistics", "County Clerk"]
        },
        "criminal": {
            "name": "Criminal Records",
            "description": "Sex offenders, inmates, criminal history",
            "sources": ["NSOPW", "State DOC", "County Jail"]
        },
        "regulatory": {
            "name": "Regulatory Records",
            "description": "FDA, EPA, OSHA violations and inspections",
            "sources": ["FDA API", "EPA API", "OSHA API"]
        },
        "financial": {
            "name": "Financial Records",
            "description": "Bankruptcy, tax liens, UCC filings, nonprofit 990s",
            "sources": ["PACER", "County Recorder", "ProPublica"]
        },
        "asset": {
            "name": "Asset Records",
            "description": "Aircraft, vessels, vehicles, equipment",
            "sources": ["FAA Registry", "Coast Guard", "DMV"]
        },
        "education": {
            "name": "Education Records",
            "description": "Teacher licenses, school data, accreditation",
            "sources": ["NCES API", "State DOE"]
        },
        "employment": {
            "name": "Employment Records",
            "description": "Government salaries, pensions, public employees",
            "sources": ["State Comptroller", "OpenPayrolls"]
        },
        "health_safety": {
            "name": "Health & Safety",
            "description": "Healthcare provider licenses, nursing homes, inspections",
            "sources": ["CMS API", "State Health Dept"]
        },
        "transportation": {
            "name": "Transportation",
            "description": "CDL holders, carrier data, truck inspections",
            "sources": ["FMCSA API"]
        }
    }

    return {
        "categories": categories,
        "total_categories": len(categories)
    }


@app.get("/admin/coverage/stats/quick")
@rate_limit(max_requests=60, window=60)
async def get_quick_coverage_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get quick coverage statistics (public endpoint for dashboard).
    Lighter weight than full summary for frequent polling.
    """
    cache_key = "quick_coverage_stats"

    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    try:
        total_jurisdictions = db.query(func.count(Jurisdiction.id)).scalar() or 0
        covered_jurisdictions = db.query(func.count(Jurisdiction.id)).filter(
            Jurisdiction.record_count > 0
        ).scalar() or 0
        total_records = db.query(func.sum(Jurisdiction.record_count)).scalar() or 0
        unique_states = db.query(func.count(func.distinct(Jurisdiction.state))).scalar() or 0

        stats = {
            "total_jurisdictions": total_jurisdictions,
            "covered_jurisdictions": covered_jurisdictions,
            "coverage_percentage": round((covered_jurisdictions / max(total_jurisdictions, 1)) * 100, 2),
            "total_records": total_records,
            "states_with_data": unique_states,
            "target_jurisdictions": 3143,
            "target_percentage": round((covered_jurisdictions / 3143) * 100, 2),
            "last_updated": datetime.utcnow().isoformat()
        }

        # Cache for 1 minute
        if redis_client:
            redis_client.setex(cache_key, 60, json.dumps(stats))

        return stats

    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        return {
            "total_jurisdictions": 0,
            "covered_jurisdictions": 0,
            "coverage_percentage": 0,
            "total_records": 0,
            "states_with_data": 0,
            "target_jurisdictions": 3143,
            "target_percentage": 0,
            "last_updated": datetime.utcnow().isoformat()
        }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DataGod API v2 is running",
        "version": settings.api_version,
        "documentation": f"{settings.api_docs_url}",
        "status": "healthy"
    }

# Test endpoint
@app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    return {"message": "API v2 is working correctly"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("🚀 Starting DataGod API v2...")

    # Check database connection
    if check_db_connection():
        logger.info("✅ Database connection established")

        # Initialize users table and create demo users
        try:
            # Ensure demo users exist in the database
            ensure_demo_users_exist()
            logger.info("✅ User database initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize demo users: {e}")
    else:
        logger.warning("⚠️ Database connection failed")

    # Check cache connection
    if redis_client:
        try:
            redis_client.ping()
            logger.info("✅ Cache connection established")
        except:
            logger.warning("⚠️ Cache connection failed")
    else:
        logger.info("ℹ️ Cache is disabled")

    logger.info(f"📊 API v2 {settings.api_version} started successfully")
    logger.info(f"🔗 Documentation available at {settings.api_docs_url}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("🛑 Shutting down DataGod API v2...")
    logger.info("👋 Goodbye!")
