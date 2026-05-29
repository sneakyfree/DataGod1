"""
Simplified DataGod API v2 - Using Pydantic Models
"""

import csv
import hashlib
import io
import json
import logging
import re
import time
import uuid
from datetime import date, datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

import pandas as pd
import redis
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import asc, desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from datagod.models import DataSource, Entity, Jurisdiction, Record, Relationship
from datagod.models import User as UserModel
from db import check_db_connection, get_db
from db_manager import DatabaseManager
from models import (
    APIInfoResponse,
    CacheStatsResponse,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    EntityCreate,
    EntityResponse,
    EntityUpdate,
    ErrorResponse,
    ExportRequest,
    ExportResponse,
    ForgotPasswordRequest,
    HealthResponse,
    IntegrationResponse,
    JurisdictionCreate,
    JurisdictionResponse,
    JurisdictionUpdate,
    LoginRequest,
    MessageResponse,
    MetricsResponse,
    RecordCreate,
    RecordResponse,
    RecordUpdate,
    RelationshipCreate,
    RelationshipResponse,
    RelationshipUpdate,
    ResetPasswordRequest,
    SearchQuery,
    SearchResponse,
    Token,
    TokenData,
    UserCreate,
    UserInDB,
    UserRegister,
    UserResponse,
    UserUpdate,
)

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
    swagger_ui_parameters={"syntaxHighlight.theme": "monokai"},
)

# Security settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes

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
        socket_connect_timeout=5,
    )
    # Test connection
    redis_client.ping()
    logger.info("✅ Redis cache connected successfully")
except Exception as e:
    logger.warning(f"⚠️ Redis cache not available: {e}")
    redis_client = None

# Initialize database manager for user operations
# Allow override for testing
_user_db_manager = None


def get_user_db_manager():
    """Get the user database manager, initializing if needed."""
    global _user_db_manager
    if _user_db_manager is None:
        _user_db_manager = DatabaseManager()
    return _user_db_manager


def set_user_db_manager(manager):
    """Set a custom user database manager (for testing)."""
    global _user_db_manager
    _user_db_manager = manager


# Rate limiting decorator
def rate_limit(max_requests: int = 100, window: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # For now, skip rate limiting if no redis (since we can't get request in this context)
            # In production, rate limiting would be handled by middleware
            if redis_client:
                # Get request from kwargs if available
                request = kwargs.get("request")
                if request:
                    client_ip = request.client.host if request.client else "unknown"
                    cache_key = f"rate_limit:{func.__name__}:{client_ip}"

                    current = redis_client.get(cache_key)
                    if current and int(current) >= max_requests:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Too many requests, rate limit exceeded ({max_requests} requests per {window} seconds)",
                        )

                    pipe = redis_client.pipeline()
                    pipe.incr(cache_key)
                    if current is None:
                        pipe.expire(cache_key, window)
                    pipe.execute()
            else:
                # In-memory rate limiting (simplified for testing)
                if hasattr(wrapper, "request_count"):
                    if time.time() - wrapper.last_reset < window:
                        if wrapper.request_count >= max_requests:
                            raise HTTPException(
                                status_code=429,
                                detail=f"Too many requests, rate limit exceeded ({max_requests} requests per {window} seconds)",
                            )
                        wrapper.request_count += 1
                    else:
                        wrapper.request_count = 1
                        wrapper.last_reset = time.time()
                else:
                    wrapper.request_count = 1
                    wrapper.last_reset = time.time()

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Password hashing
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# User database operations - using DatabaseManager instead of in-memory fake_users_db
def get_user_from_db(username: str) -> Optional[UserInDB]:
    """Get user from database by username."""
    user_dict = get_user_db_manager().get_user_for_auth(username)
    if user_dict:
        return UserInDB(**user_dict)
    return None


def authenticate_user_from_db(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user against database."""
    # Check if account is locked
    if get_user_db_manager().check_user_locked(username):
        return None

    user = get_user_from_db(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        # Record failed login attempt
        get_user_db_manager().record_login(username, success=False)
        return None

    # Record successful login
    get_user_db_manager().record_login(username, success=True)
    return user


def ensure_demo_users_exist():
    """Ensure demo users exist in the database on startup."""
    # Check if admin user exists
    if not get_user_db_manager().get_user_by_username("admin"):
        get_user_db_manager().create_user(
            username="admin",
            email="admin@datagod.com",
            hashed_password=get_password_hash("admin123"),
            full_name="DataGod Admin",
            roles=["admin", "user"],
            disabled=False,
        )
        logger.info("Created demo admin user")

    # Check if regular user exists
    if not get_user_db_manager().get_user_by_username("user"):
        get_user_db_manager().create_user(
            username="user",
            email="user@datagod.com",
            hashed_password=get_password_hash("user123"),
            full_name="DataGod User",
            roles=["user"],
            disabled=False,
        )
        logger.info("Created demo user")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> UserResponse:
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

    user = get_user_from_db(username=token_data.username)
    if user is None:
        raise credentials_exception

    request.state.user = user
    return UserResponse(**user.dict())


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def has_role(required_roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs (injected by FastAPI dependency)
            current_user = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )
            user_roles = current_user.roles if hasattr(current_user, "roles") else []
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operation not permitted",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Health and monitoring endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_status = "healthy" if check_db_connection() else "unhealthy"
    cache_status = "healthy" if redis_client else "disabled"

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        database=db_status,
        cache=cache_status,
        api_version=settings.api_version,
    )


@app.get("/metrics", response_model=MetricsResponse)
@rate_limit(max_requests=10, window=60)
async def get_metrics():
    """Get system metrics"""
    return MetricsResponse(
        status="metrics available",
        timestamp=datetime.utcnow(),
        metrics={
            "api_calls": 0,
            "database_queries": 0,
            "cache_hits": 0,
            "active_connections": 0,
        },
    )


# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return access token"""
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
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/refresh-token", response_model=Token)
async def refresh_access_token(token: str = Depends(oauth2_scheme)):
    """Refresh access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        user = get_user_from_db(username=username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_token = create_access_token(
            data={"sub": user.username, "roles": user.roles},
            expires_delta=access_token_expires,
        )

        return Token(
            access_token=new_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


# Public authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register_user(user: UserRegister):
    """
    Register a new user account.

    This is the public registration endpoint. New users are assigned the 'user' role.
    """
    # Validate email format
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
        )

    # Validate username (alphanumeric and underscores only)
    if not re.match(r"^[a-zA-Z0-9_]+$", user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain letters, numbers, and underscores",
        )

    # Check if username already exists
    if get_user_db_manager().get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    if get_user_db_manager().get_user_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password and create user in database
    hashed_password = get_password_hash(user.password)
    user_id = get_user_db_manager().create_user(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        roles=["user"],  # Default role for new registrations
        disabled=False,
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    logger.info(f"New user registered: {user.username}")

    # Return the created user
    created_user = get_user_db_manager().get_user_by_username(user.username)
    return UserResponse(**created_user)


@app.post("/auth/login", response_model=Token)
async def login(credentials: LoginRequest):
    """
    Authenticate user with username and password (JSON body).

    This is an alternative to the OAuth2 /token endpoint that accepts JSON.
    """
    user = authenticate_user_from_db(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/auth/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request a password reset.

    Sends a password reset token (in production, this would be emailed).
    For security, always returns success even if email doesn't exist.
    """
    # Generate reset token
    reset_token = str(uuid.uuid4())

    # Try to set token in database (only succeeds if email exists)
    if get_user_db_manager().set_password_reset_token(
        request.email, reset_token, expires_hours=1
    ):
        # In production, send email with reset link
        logger.info(
            f"Password reset token generated for {request.email}: {reset_token}"
        )

    # Always return success for security (don't reveal if email exists)
    return MessageResponse(
        message="If your email is registered, you will receive a password reset link"
    )


@app.post("/auth/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using a reset token.
    """
    # Get user by reset token (validates token and expiry)
    user = get_user_db_manager().get_user_by_reset_token(request.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    hashed_password = get_password_hash(request.new_password)
    get_user_db_manager().update_user(user["id"], hashed_password=hashed_password)

    # Clear the reset token
    get_user_db_manager().clear_password_reset_token(user["id"])

    logger.info(f"Password reset successful for user: {user['username']}")

    return MessageResponse(message="Password has been reset successfully")


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


# User management endpoints
@app.post("/users", response_model=UserResponse)
@has_role(["admin"])
async def create_user(
    user: UserCreate, current_user: UserResponse = Depends(get_current_active_user)
):
    """Create a new user (admin only)"""
    if get_user_db_manager().get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if get_user_db_manager().get_user_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
    user_id = get_user_db_manager().create_user(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        roles=user.roles or ["user"],
        disabled=False,
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    created_user = get_user_db_manager().get_user_by_username(user.username)
    return UserResponse(**created_user)


@app.get("/users", response_model=List[UserResponse])
@has_role(["admin"])
async def get_users(current_user: UserResponse = Depends(get_current_active_user)):
    """Get all users (admin only)"""
    users = get_user_db_manager().list_users()
    return [UserResponse(**user) for user in users]


@app.get("/users/{username}", response_model=UserResponse)
@has_role(["admin"])
async def get_user_by_username(
    username: str, current_user: UserResponse = Depends(get_current_active_user)
):
    """Get user by username (admin only)"""
    user = get_user_db_manager().get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse(**user)


# Jurisdiction endpoints
@app.post("/jurisdictions", response_model=JurisdictionResponse)
@has_role(["admin", "user"])
async def create_jurisdiction(
    jurisdiction: JurisdictionCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Create a new jurisdiction"""
    try:
        db_jurisdiction = Jurisdiction(**jurisdiction.dict())
        db.add(db_jurisdiction)
        db.commit()
        db.refresh(db_jurisdiction)
        return JurisdictionResponse.from_orm(db_jurisdiction)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating jurisdiction: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@app.get("/jurisdictions", response_model=List[JurisdictionResponse])
@rate_limit(max_requests=50, window=60)
async def get_jurisdictions(
    db: Session = Depends(get_db),
    name: Optional[str] = None,
    state: Optional[str] = None,
    county: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
):
    """Get all jurisdictions with filtering and pagination"""
    query = db.query(Jurisdiction)

    if name:
        query = query.filter(Jurisdiction.name.ilike(f"%{name}%"))
    if state:
        query = query.filter(Jurisdiction.state == state)
    if county:
        query = query.filter(Jurisdiction.county == county)

    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Jurisdiction, sort_by)))
    else:
        query = query.order_by(asc(getattr(Jurisdiction, sort_by)))

    jurisdictions = query.offset(offset).limit(limit).all()
    return [JurisdictionResponse.from_orm(j) for j in jurisdictions]


@app.get("/jurisdictions/{jurisdiction_id}", response_model=JurisdictionResponse)
@rate_limit(max_requests=50, window=60)
async def get_jurisdiction(jurisdiction_id: int, db: Session = Depends(get_db)):
    """Get a specific jurisdiction by ID"""
    jurisdiction = (
        db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    )
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )
    return JurisdictionResponse.from_orm(jurisdiction)


@app.put("/jurisdictions/{jurisdiction_id}", response_model=JurisdictionResponse)
@has_role(["admin", "user"])
async def update_jurisdiction(
    jurisdiction_id: int,
    jurisdiction_update: JurisdictionUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Update a jurisdiction"""
    jurisdiction = (
        db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    )
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )

    for key, value in jurisdiction_update.dict(exclude_unset=True).items():
        setattr(jurisdiction, key, value)

    db.commit()
    db.refresh(jurisdiction)
    return JurisdictionResponse.from_orm(jurisdiction)


@app.delete("/jurisdictions/{jurisdiction_id}", response_model=dict)
@has_role(["admin"])
async def delete_jurisdiction(
    jurisdiction_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Delete a jurisdiction (admin only)"""
    jurisdiction = (
        db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    )
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )

    db.delete(jurisdiction)
    db.commit()
    return {"message": "Jurisdiction deleted successfully"}


# Data source endpoints
@app.post("/data-sources", response_model=DataSourceResponse)
@has_role(["admin", "user"])
async def create_data_source(
    data_source: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Create a new data source"""
    try:
        jurisdiction = (
            db.query(Jurisdiction)
            .filter(Jurisdiction.id == data_source.jurisdiction_id)
            .first()
        )
        if not jurisdiction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Jurisdiction not found"
            )

        db_data_source = DataSource(**data_source.dict())
        db.add(db_data_source)
        db.commit()
        db.refresh(db_data_source)
        return DataSourceResponse.from_orm(db_data_source)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@app.get("/data-sources", response_model=List[DataSourceResponse])
@rate_limit(max_requests=50, window=60)
async def get_data_sources(
    db: Session = Depends(get_db),
    jurisdiction_id: Optional[int] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "id",
    sort_order: str = "asc",
):
    """Get all data sources with filtering and pagination"""
    query = db.query(DataSource)

    if jurisdiction_id:
        query = query.filter(DataSource.jurisdiction_id == jurisdiction_id)
    if source_type:
        query = query.filter(DataSource.source_type == source_type)
    if status:
        query = query.filter(DataSource.status == status)

    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(DataSource, sort_by)))
    else:
        query = query.order_by(asc(getattr(DataSource, sort_by)))

    data_sources = query.offset(offset).limit(limit).all()
    return [DataSourceResponse.from_orm(ds) for ds in data_sources]


@app.get("/data-sources/{data_source_id}", response_model=DataSourceResponse)
@rate_limit(max_requests=50, window=60)
async def get_data_source(data_source_id: int, db: Session = Depends(get_db)):
    """Get a specific data source by ID"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found"
        )
    return DataSourceResponse.from_orm(data_source)


# Record endpoints
@app.post("/records", response_model=RecordResponse)
@has_role(["admin", "user"])
async def create_record(
    record: RecordCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Create a new record"""
    try:
        jurisdiction = (
            db.query(Jurisdiction)
            .filter(Jurisdiction.id == record.jurisdiction_id)
            .first()
        )
        if not jurisdiction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Jurisdiction not found"
            )

        if record.data_source_id:
            data_source = (
                db.query(DataSource)
                .filter(DataSource.id == record.data_source_id)
                .first()
            )
            if not data_source:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data source not found",
                )

        db_record = Record(**record.dict())
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return RecordResponse.from_orm(db_record)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating record: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@app.get("/records", response_model=List[RecordResponse])
@rate_limit(max_requests=50, window=60)
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
    sort_order: str = "desc",
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

    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Record, sort_by)))
    else:
        query = query.order_by(asc(getattr(Record, sort_by)))

    records = query.offset(offset).limit(limit).all()
    return [RecordResponse.from_orm(r) for r in records]


@app.get("/records/{record_id}", response_model=RecordResponse)
@rate_limit(max_requests=50, window=60)
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """Get a specific record by ID"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    return RecordResponse.from_orm(record)


# Entity endpoints
@app.post("/entities", response_model=EntityResponse)
@has_role(["admin", "user"])
async def create_entity(
    entity: EntityCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Create a new entity"""
    try:
        db_entity = Entity(**entity.dict())
        db.add(db_entity)
        db.commit()
        db.refresh(db_entity)
        return EntityResponse.from_orm(db_entity)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@app.get("/entities", response_model=List[EntityResponse])
@rate_limit(max_requests=50, window=60)
async def get_entities(
    db: Session = Depends(get_db),
    entity_type: Optional[str] = None,
    jurisdiction_id: Optional[int] = None,
    name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "entity_name",
    sort_order: str = "asc",
):
    """Get all entities with filtering and pagination"""
    query = db.query(Entity)

    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if jurisdiction_id:
        query = query.filter(Entity.jurisdiction_id == jurisdiction_id)
    if name:
        query = query.filter(Entity.entity_name.ilike(f"%{name}%"))

    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Entity, sort_by)))
    else:
        query = query.order_by(asc(getattr(Entity, sort_by)))

    entities = query.offset(offset).limit(limit).all()
    return [EntityResponse.from_orm(e) for e in entities]


@app.get("/entities/{entity_id}", response_model=EntityResponse)
@rate_limit(max_requests=50, window=60)
async def get_entity(entity_id: int, db: Session = Depends(get_db)):
    """Get a specific entity by ID"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found"
        )
    return EntityResponse.from_orm(entity)


# Relationship endpoints
@app.post("/relationships", response_model=RelationshipResponse)
@has_role(["admin", "user"])
async def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Create a new relationship"""
    try:
        entity1 = db.query(Entity).filter(Entity.id == relationship.entity1_id).first()
        entity2 = db.query(Entity).filter(Entity.id == relationship.entity2_id).first()

        if not entity1 or not entity2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or both entities not found",
            )

        if relationship.record_id:
            record = (
                db.query(Record).filter(Record.id == relationship.record_id).first()
            )
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Record not found"
                )

        db_relationship = Relationship(**relationship.dict())
        db.add(db_relationship)
        db.commit()
        db.refresh(db_relationship)
        return RelationshipResponse.from_orm(db_relationship)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@app.get("/relationships", response_model=List[RelationshipResponse])
@rate_limit(max_requests=50, window=60)
async def get_relationships(
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    relationship_type: Optional[str] = None,
    record_id: Optional[int] = None,
    confidence_min: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "confidence_score",
    sort_order: str = "desc",
):
    """Get all relationships with filtering and pagination"""
    query = db.query(Relationship)

    if entity_id:
        query = query.filter(
            or_(
                Relationship.entity1_id == entity_id,
                Relationship.entity2_id == entity_id,
            )
        )
    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type)
    if record_id:
        query = query.filter(Relationship.record_id == record_id)
    if confidence_min:
        query = query.filter(Relationship.confidence_score >= confidence_min)

    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Relationship, sort_by)))
    else:
        query = query.order_by(asc(getattr(Relationship, sort_by)))

    relationships = query.offset(offset).limit(limit).all()
    return [RelationshipResponse.from_orm(r) for r in relationships]


@app.get("/relationships/{relationship_id}", response_model=RelationshipResponse)
@rate_limit(max_requests=50, window=60)
async def get_relationship(relationship_id: int, db: Session = Depends(get_db)):
    """Get a specific relationship by ID"""
    relationship = (
        db.query(Relationship).filter(Relationship.id == relationship_id).first()
    )
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found"
        )
    return RelationshipResponse.from_orm(relationship)


# Advanced search endpoint
@app.post("/search", response_model=SearchResponse)
@rate_limit(max_requests=30, window=60)
async def advanced_search(
    search_query: SearchQuery,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Advanced search across all data types with full-text search"""
    query = db.query(Record)

    if search_query.query:
        query = query.filter(
            or_(
                Record.title.ilike(f"%{search_query.query}%"),
                Record.description.ilike(f"%{search_query.query}%"),
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

    if search_query.sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Record, search_query.sort_by)))
    else:
        query = query.order_by(asc(getattr(Record, search_query.sort_by)))

    total_count = query.count()
    records = (
        query.offset((search_query.page - 1) * search_query.page_size)
        .limit(search_query.page_size)
        .all()
    )

    return SearchResponse(
        records=[RecordResponse.from_orm(r) for r in records],
        total_count=total_count,
        page=search_query.page,
        page_size=search_query.page_size,
        total_pages=(total_count + search_query.page_size - 1)
        // search_query.page_size,
    )


# Data export endpoints
@app.post("/export")
@rate_limit(max_requests=5, window=60)
async def export_data(
    export_request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Export data in various formats with advanced filtering"""
    query = db.query(Record)

    if export_request.query:
        if export_request.query.query:
            query = query.filter(
                or_(
                    Record.title.ilike(f"%{export_request.query.query}%"),
                    Record.description.ilike(f"%{export_request.query.query}%"),
                )
            )

        if export_request.query.jurisdiction_ids:
            query = query.filter(
                Record.jurisdiction_id.in_(export_request.query.jurisdiction_ids)
            )

        if export_request.query.record_types:
            query = query.filter(
                Record.record_type.in_(export_request.query.record_types)
            )

        if export_request.query.date_from:
            query = query.filter(Record.date >= export_request.query.date_from)

        if export_request.query.date_to:
            query = query.filter(Record.date <= export_request.query.date_to)

        if export_request.query.amount_min:
            query = query.filter(Record.amount >= export_request.query.amount_min)

        if export_request.query.amount_max:
            query = query.filter(Record.amount <= export_request.query.amount_max)

    query = query.limit(settings.max_export_records)
    records = query.all()

    if not records:
        return ExportResponse(
            records=[], count=0, format="json", timestamp=datetime.utcnow()
        )

    if export_request.format == "csv":
        output = io.StringIO()
        fieldnames = [
            "id",
            "title",
            "description",
            "record_type",
            "amount",
            "date",
            "jurisdiction_id",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow(
                {
                    "id": record.id,
                    "title": record.title,
                    "description": record.description,
                    "record_type": record.record_type,
                    "amount": record.amount,
                    "date": record.date,
                    "jurisdiction_id": record.jurisdiction_id,
                }
            )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )

    elif export_request.format == "excel":
        df = pd.DataFrame(
            [
                {
                    "id": record.id,
                    "title": record.title,
                    "description": record.description,
                    "record_type": record.record_type,
                    "amount": record.amount,
                    "date": record.date,
                    "jurisdiction_id": record.jurisdiction_id,
                }
                for record in records
            ]
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Records")

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"},
        )

    else:
        return ExportResponse(
            records=[jsonable_encoder(r) for r in records],
            count=len(records),
            format="json",
            timestamp=datetime.utcnow(),
        )


# Integration endpoints
@app.post("/integrate/neural-network", response_model=IntegrationResponse)
@has_role(["admin", "user"])
@rate_limit(max_requests=10, window=60)
async def integrate_neural_network(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Integrate neural network processing for a record"""
    if not settings.enable_neural_network_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neural network integration is disabled",
        )

    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    def process_with_neural_network():
        try:
            from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNN

            nn = MortgageDataGatheringNN()
            processed_data = nn.process_record(record)

            if record.metadata is None:
                record.metadata = {}
            record.metadata["neural_network_processed"] = True
            record.metadata["neural_network_results"] = processed_data

            db.commit()
            logger.info(f"Neural network processing completed for record {record_id}")

        except Exception as e:
            logger.error(
                f"Neural network processing failed for record {record_id}: {e}"
            )
            db.rollback()

    background_tasks.add_task(process_with_neural_network)

    return IntegrationResponse(
        message="Neural network processing started",
        record_id=record_id,
        status="processing",
    )


@app.post("/integrate/scraper", response_model=IntegrationResponse)
@has_role(["admin", "user"])
@rate_limit(max_requests=10, window=60)
async def integrate_scraper(
    jurisdiction_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Integrate scraper processing for a jurisdiction"""
    if not settings.enable_scraper_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scraper integration is disabled",
        )

    jurisdiction = (
        db.query(Jurisdiction).filter(Jurisdiction.id == jurisdiction_id).first()
    )
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )

    def process_with_scraper():
        try:
            from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

            orchestrator = ScraperOrchestrator()
            scraped_data = orchestrator.scrape_jurisdiction(jurisdiction)

            for data in scraped_data:
                record = Record(
                    jurisdiction_id=jurisdiction.id,
                    record_type=data.get("record_type", "scraped"),
                    title=data.get("title", "Scraped Data"),
                    description=data.get("description", ""),
                    amount=data.get("amount"),
                    date=data.get("date"),
                    metadata=data.get("metadata", {}),
                    raw_data=data,
                )
                db.add(record)

            db.commit()
            logger.info(
                f"Scraper processing completed for jurisdiction {jurisdiction_id}"
            )

        except Exception as e:
            logger.error(
                f"Scraper processing failed for jurisdiction {jurisdiction_id}: {e}"
            )
            db.rollback()

    background_tasks.add_task(process_with_scraper)

    return IntegrationResponse(
        message="Scraper processing started",
        jurisdiction_id=jurisdiction_id,
        status="processing",
    )


# Cache management endpoints
@app.get("/cache/stats", response_model=CacheStatsResponse)
@has_role(["admin"])
async def get_cache_stats(
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Get cache statistics"""
    if not redis_client:
        return CacheStatsResponse(status="cache disabled", stats={})

    try:
        info = redis_client.info()
        return CacheStatsResponse(
            status="healthy",
            stats={
                "used_memory": info.get("used_memory", 0),
                "keys": info.get("db0", {}).get("keys", 0),
                "uptime": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0),
            },
        )
    except Exception as e:
        return CacheStatsResponse(status="error", stats={"error": str(e)})


@app.delete("/cache/clear", response_model=dict)
@has_role(["admin"])
async def clear_cache(current_user: UserResponse = Depends(get_current_active_user)):
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
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Root endpoint
@app.get("/", response_model=APIInfoResponse)
async def root():
    """Root endpoint"""
    return APIInfoResponse(
        message="DataGod API v2 is running",
        version=settings.api_version,
        documentation=settings.api_docs_url,
        status="healthy",
    )


# Test endpoint
@app.get("/test", response_model=dict)
async def test_endpoint():
    """Test endpoint"""
    return {"message": "API v2 is working correctly"}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("🚀 Starting DataGod API v2...")

    if check_db_connection():
        logger.info("✅ Database connection established")
        # Initialize database tables and create demo users
        try:
            get_user_db_manager().init_database()
            ensure_demo_users_exist()
            logger.info("✅ User database initialized")
        except Exception as e:
            logger.warning(f"⚠️ User database initialization warning: {e}")
    else:
        logger.warning("⚠️ Database connection failed")

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
