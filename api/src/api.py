import json
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

import redis
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from datagod.models.data_source import DataSource
from datagod.models.entity import Entity
from datagod.models.jurisdiction import Jurisdiction
from datagod.models.record import Record
from datagod.models.relationship import Relationship
from db import get_db

# Initialize FastAPI app
app = FastAPI(title=settings.api_title, version=settings.api_version)

# Security settings
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Redis connection for caching (if available)
redis_client = None
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
except:
    # Redis not available, continue without caching
    pass


# Rate limiting decorator
def rate_limit(max_requests: int = 100, window: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Simple in-memory rate limiting (in production, use Redis)
            if hasattr(wrapper, "request_count"):
                if time.time() - wrapper.last_reset < window:
                    if wrapper.request_count >= max_requests:
                        raise HTTPException(
                            status_code=429,
                            detail="Too many requests, rate limit exceeded",
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


# User model
class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


# Token model
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Fake database for demonstration
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "email": "johndoe@example.com",
        "full_name": "John Doe",
        "hashed_password": "$2b$12$1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "disabled": False,
    }
}


# Password hashing
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
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
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# API endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(username: str, password: str):
    user = authenticate_user(fake_users_db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Protected endpoint example
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# Advanced search endpoint
@app.get("/search")
@rate_limit(max_requests=50, window=60)
async def advanced_search(
    db: Session = Depends(get_db),
    query: Optional[str] = None,
    jurisdiction_id: Optional[int] = None,
    record_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Advanced search endpoint for records with multiple filter options
    """
    # Build query
    records_query = db.query(Record)

    # Apply filters
    if query:
        # Full text search
        records_query = records_query.filter(
            Record.title.ilike(f"%{query}%") | Record.description.ilike(f"%{query}%")
        )

    if jurisdiction_id:
        records_query = records_query.filter(Record.jurisdiction_id == jurisdiction_id)

    if record_type:
        records_query = records_query.filter(Record.record_type == record_type)

    if date_from:
        records_query = records_query.filter(Record.date >= date_from)

    if date_to:
        records_query = records_query.filter(Record.date <= date_to)

    if amount_min:
        records_query = records_query.filter(Record.amount >= amount_min)

    if amount_max:
        records_query = records_query.filter(Record.amount <= amount_max)

    # Apply pagination
    records = records_query.offset(offset).limit(limit).all()

    # Return results
    return {
        "records": records,
        "count": records_query.count(),
        "offset": offset,
        "limit": limit,
    }


# Data export endpoint
@app.get("/export")
@rate_limit(max_requests=10, window=60)
async def export_data(
    db: Session = Depends(get_db),
    format: str = "json",  # json, csv, xml
    jurisdiction_id: Optional[int] = None,
    record_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    Export data in various formats
    """
    # Build query
    records_query = db.query(Record)

    # Apply filters
    if jurisdiction_id:
        records_query = records_query.filter(Record.jurisdiction_id == jurisdiction_id)

    if record_type:
        records_query = records_query.filter(Record.record_type == record_type)

    if date_from:
        records_query = records_query.filter(Record.date >= date_from)

    if date_to:
        records_query = records_query.filter(Record.date <= date_to)

    records = records_query.all()

    # Format data based on requested format
    if format == "csv":
        # Convert to CSV format
        import csv
        from io import StringIO

        output = StringIO()
        if records:
            fieldnames = records[0].__dict__.keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record.__dict__)
        return output.getvalue()

    elif format == "xml":
        # Convert to XML format
        import xml.etree.ElementTree as ET

        root = ET.Element("records")
        for record in records:
            record_elem = ET.SubElement(root, "record")
            for key, value in record.__dict__.items():
                if key != "_sa_instance_state":
                    elem = ET.SubElement(record_elem, key)
                    elem.text = str(value)
        return ET.tostring(root, encoding="unicode")

    else:  # JSON
        return {"records": [record.__dict__ for record in records]}


# Caching endpoint
@app.get("/cache/{key}")
async def get_cached_data(key: str):
    """
    Get data from cache
    """
    if redis_client:
        cached_data = redis_client.get(key)
        if cached_data:
            return {"cached": True, "data": json.loads(cached_data)}
    return {"cached": False, "data": None}


@app.post("/cache/{key}")
async def set_cached_data(key: str, data: Dict[str, Any], expire: int = 3600):
    """
    Set data in cache
    """
    if redis_client:
        redis_client.setex(key, expire, json.dumps(data))
        return {"status": "cached"}
    return {"status": "cache not available"}


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """
    Get system metrics
    """
    return {"status": "metrics available", "timestamp": datetime.utcnow().isoformat()}


# Jurisdiction endpoints
@app.get("/jurisdictions")
async def get_jurisdictions(db: Session = Depends(get_db)):
    """
    Get all jurisdictions
    """
    jurisdictions = db.query(Jurisdiction).all()
    return jurisdictions


@app.get("/jurisdictions/{id}")
async def get_jurisdiction(id: int, db: Session = Depends(get_db)):
    """
    Get a specific jurisdiction
    """
    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.id == id).first()
    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")
    return jurisdiction


# Data source endpoints
@app.get("/data-sources")
async def get_data_sources(db: Session = Depends(get_db)):
    """
    Get all data sources
    """
    data_sources = db.query(DataSource).all()
    return data_sources


# Record endpoints
@app.get("/records")
async def get_records(db: Session = Depends(get_db), limit: int = 100, offset: int = 0):
    """
    Get all records with pagination
    """
    records = db.query(Record).offset(offset).limit(limit).all()
    return records


@app.get("/records/{id}")
async def get_record(id: int, db: Session = Depends(get_db)):
    """
    Get a specific record
    """
    record = db.query(Record).filter(Record.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


# Entity endpoints
@app.get("/entities")
async def get_entities(
    db: Session = Depends(get_db), limit: int = 100, offset: int = 0
):
    """
    Get all entities with pagination
    """
    entities = db.query(Entity).offset(offset).limit(limit).all()
    return entities


@app.get("/entities/{id}")
async def get_entity(id: int, db: Session = Depends(get_db)):
    """
    Get a specific entity
    """
    entity = db.query(Entity).filter(Entity.id == id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


# Relationship endpoints
@app.get("/relationships")
async def get_relationships(
    db: Session = Depends(get_db), limit: int = 100, offset: int = 0
):
    """
    Get all relationships with pagination
    """
    relationships = db.query(Relationship).offset(offset).limit(limit).all()
    return relationships


@app.get("/relationships/{id}")
async def get_relationship(id: int, db: Session = Depends(get_db)):
    """
    Get a specific relationship
    """
    relationship = db.query(Relationship).filter(Relationship.id == id).first()
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return relationship


# Add middleware for gzip compression and trusted hosts
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


# Add a simple test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "API is working"}
