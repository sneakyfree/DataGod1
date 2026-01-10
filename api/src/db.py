"""
Database connection and session management for the DataGod API.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datagod.config.settings import (
    DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT, DB_POOL_RECYCLE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database engine with connection pooling
# For SQLite, we need to disable check_same_thread for multi-threaded usage
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Create base class for models
Base = declarative_base()

# Create session factory with enhanced configuration
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db():
    """Dependency to get database session for FastAPI endpoints."""
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


def check_db_connection() -> bool:
    """Health check function to verify database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def init_db():
    """Initialize the database by creating all tables."""
    try:
        from datagod.models import Base as DataGodBase
        DataGodBase.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


def get_db_stats() -> dict:
    """Get database pool statistics."""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow()
    }
