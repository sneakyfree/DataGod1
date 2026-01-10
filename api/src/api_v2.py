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
from datagod.models.jurisdiction import Jurisdiction
from datagod.models.data_source import DataSource
from datagod.models.record import Record
from datagod.models.entity import Entity
from datagod.models.relationship import Relationship
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
async def get_metrics():
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
@app.post("/jurisdictions", response_model=Jurisdiction)
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

@app.get("/jurisdictions", response_model=List[Jurisdiction])
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_jurisdictions(
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

@app.get("/jurisdictions/{jurisdiction_id}", response_model=Jurisdiction)
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_jurisdiction(
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

@app.put("/jurisdictions/{jurisdiction_id}", response_model=Jurisdiction)
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
@app.post("/data-sources", response_model=DataSource)
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

@app.get("/data-sources", response_model=List[DataSource])
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_data_sources(
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

@app.get("/data-sources/{data_source_id}", response_model=DataSource)
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_data_source(
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
@app.post("/records", response_model=Record)
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

@app.get("/records", response_model=List[Record])
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_records(
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

@app.get("/records/{record_id}", response_model=Record)
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_record(
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
@app.post("/entities", response_model=Entity)
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

@app.get("/entities", response_model=List[Entity])
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_entities(
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

@app.get("/entities/{entity_id}", response_model=Entity)
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_entity(
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

# Relationship endpoints
@app.post("/relationships", response_model=Relationship)
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

@app.get("/relationships", response_model=List[Relationship])
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_relationships(
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

@app.get("/relationships/{relationship_id}", response_model=Relationship)
@rate_limit(max_requests=50, window=60)
@cache_response(expiration=300)
async def get_relationship(
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
