"""
DataGod Database Models
SQLAlchemy models for all database entities
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from datetime import datetime
import logging

from datagod.config.settings import (
    DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT, DB_POOL_RECYCLE
)

logger = logging.getLogger(__name__)

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    echo=False  # Set to True for SQL query logging in development
)

# Create the declarative base
Base = declarative_base()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread safety
db_session = scoped_session(SessionLocal)

# Timestamp mixin for created_at/updated_at
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Jurisdiction(Base, TimestampMixin):
    """Represents a jurisdiction (county, city, state)"""
    __tablename__ = 'jurisdictions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    state = Column(String(2), nullable=True, index=True)
    county = Column(String(100), nullable=True, index=True)
    type = Column(String(50), nullable=True)  # 'county', 'city', 'state', etc.
    api_available = Column(Boolean, default=False)
    scraper_needed = Column(Boolean, default=True)
    population = Column(Integer, nullable=True)
    area_sq_miles = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    contact_info = Column(JSON, nullable=True)  # Contact details
    jurisdiction_metadata = Column(JSON, nullable=True)     # Additional jurisdiction data

    # Relationships
    data_sources = relationship("DataSource", back_populates="jurisdiction", cascade="all, delete-orphan")
    records = relationship("Record", back_populates="jurisdiction", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_jurisdiction_state_county', 'state', 'county'),
        Index('idx_jurisdiction_type', 'type'),
        Index('idx_jurisdiction_api_available', 'api_available'),
    )

    def __repr__(self):
        return f"<Jurisdiction(id={self.id}, name='{self.name}', state='{self.state}')>"


class DataSource(Base, TimestampMixin):
    """Represents a data source for a jurisdiction"""
    __tablename__ = 'data_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    source_name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'api', 'scraper', 'manual'
    api_endpoint = Column(String(1000), nullable=True)
    api_key = Column(String(500), nullable=True)  # Encrypted in production
    status = Column(String(50), default='active')  # 'active', 'inactive', 'error'
    last_scraped = Column(DateTime, nullable=True)
    next_scheduled_scrape = Column(DateTime, nullable=True)
    scrape_interval_hours = Column(Integer, default=24)
    error_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)  # Source-specific configuration
    source_metadata = Column(JSON, nullable=True)  # Additional source data

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="data_sources")
    records = relationship("Record", back_populates="data_source", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_data_source_jurisdiction', 'jurisdiction_id'),
        Index('idx_data_source_type', 'source_type'),
        Index('idx_data_source_status', 'status'),
        Index('idx_data_source_last_scraped', 'last_scraped'),
    )

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.source_name}', type='{self.source_type}')>"


class Record(Base, TimestampMixin):
    """Represents a public record"""
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)

    # Record identification
    record_id = Column(String(255), nullable=True, index=True)  # External record ID
    record_type = Column(String(100), nullable=False, index=True)  # 'property_deed', 'mortgage', 'ucc', etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Financial data
    amount = Column(Float, nullable=True)
    loan_amount = Column(Float, nullable=True)
    sale_amount = Column(Float, nullable=True)

    # Date information
    date = Column(DateTime, nullable=True, index=True)
    recording_date = Column(DateTime, nullable=True)
    filing_date = Column(DateTime, nullable=True)

    # Location data
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Parties involved
    grantor = Column(String(255), nullable=True)  # Seller/Debtor
    grantee = Column(String(255), nullable=True)  # Buyer/Creditor
    borrower = Column(String(255), nullable=True)
    lender = Column(String(255), nullable=True)

    # Legal information
    document_number = Column(String(100), nullable=True)
    book_page = Column(String(100), nullable=True)
    instrument_number = Column(String(100), nullable=True)

    # Status and quality
    status = Column(String(50), default='active')  # 'active', 'superseded', 'duplicate', 'error'
    quality_score = Column(Float, default=1.0)  # 0.0 to 1.0
    confidence_level = Column(Float, default=1.0)  # 0.0 to 1.0

    # URLs and external references
    url = Column(String(1000), nullable=True)
    document_url = Column(String(1000), nullable=True)

    # Raw and processed data
    raw_data = Column(JSON, nullable=True)      # Original scraped data
    processed_data = Column(JSON, nullable=True)  # Cleaned/processed data
    entities = Column(JSON, nullable=True)      # Extracted entities
    relationships = Column(JSON, nullable=True) # Entity relationships

    # Metadata
    tags = Column(JSON, nullable=True)          # Categorization tags
    record_metadata = Column(JSON, nullable=True)      # Additional record data

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="records")
    data_source = relationship("DataSource", back_populates="records")

    # Indexes
    __table_args__ = (
        Index('idx_record_jurisdiction', 'jurisdiction_id'),
        Index('idx_record_data_source', 'data_source_id'),
        Index('idx_record_type', 'record_type'),
        Index('idx_record_date', 'date'),
        Index('idx_record_status', 'status'),
        Index('idx_record_amount', 'amount'),
        Index('idx_record_grantor', 'grantor'),
        Index('idx_record_grantee', 'grantee'),
        Index('idx_record_address', 'address'),
        Index('idx_record_city_state', 'city', 'state'),
    )

    def __repr__(self):
        return f"<Record(id={self.id}, type='{self.record_type}', title='{self.title[:50]}...')>"


class Entity(Base, TimestampMixin):
    """Represents entities mentioned in records (people, companies, properties)"""
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)  # 'person', 'company', 'property', 'government'
    entity_id = Column(String(255), nullable=True, index=True)  # External ID if available

    # Contact information
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    # Business information
    business_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    incorporation_date = Column(DateTime, nullable=True)

    # Person information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)

    # Property information
    property_type = Column(String(50), nullable=True)
    parcel_id = Column(String(100), nullable=True)

    # Status and verification
    status = Column(String(50), default='active')  # 'active', 'inactive', 'verified', 'unverified'
    verification_date = Column(DateTime, nullable=True)
    verification_source = Column(String(255), nullable=True)

    # Additional data
    description = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)         # Additional structured data
    entity_metadata = Column(JSON, nullable=True)     # Additional metadata

    # Indexes
    __table_args__ = (
        Index('idx_entity_name_type', 'entity_name', 'entity_type'),
        Index('idx_entity_id', 'entity_id'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_entity_city_state', 'city', 'state'),
    )

    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.entity_name}', type='{self.entity_type}')>"


class Relationship(Base, TimestampMixin):
    """Represents relationships between entities"""
    __tablename__ = 'relationships'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationship participants
    entity1_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    entity2_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    record_id = Column(Integer, ForeignKey('records.id'), nullable=False)

    # Relationship details
    relationship_type = Column(String(100), nullable=False)  # 'owner', 'lender', 'borrower', 'agent', etc.
    role1 = Column(String(100), nullable=True)  # Entity1's role in the relationship
    role2 = Column(String(100), nullable=True)  # Entity2's role in the relationship

    # Context and evidence
    context = Column(Text, nullable=True)      # Description of the relationship context
    evidence = Column(JSON, nullable=True)     # Supporting evidence from records
    confidence_score = Column(Float, default=1.0)  # Confidence in the relationship

    # Temporal information
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), default='active')  # 'active', 'inactive', 'disputed'

    # Additional data
    relationship_metadata = Column(JSON, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_relationship_entities', 'entity1_id', 'entity2_id'),
        Index('idx_relationship_record', 'record_id'),
        Index('idx_relationship_type', 'relationship_type'),
        Index('idx_relationship_status', 'status'),
    )

    def __repr__(self):
        return f"<Relationship(id={self.id}, type='{self.relationship_type}', entities={self.entity1_id}-{self.entity2_id})>"


class User(Base, TimestampMixin):
    """
    Represents a user in the DataGod system.

    This model handles authentication, authorization, and user profile data.
    Supports:
    - Username/email authentication
    - Role-based access control (RBAC)
    - Password reset flow with tokens
    - Email verification
    - Subscription tracking
    """
    __tablename__ = 'users'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication fields
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255), nullable=True)

    # Account status
    disabled = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Roles and permissions (stored as JSON array)
    roles = Column(JSON, default=lambda: ["user"], nullable=False)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Login tracking
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    last_failed_login = Column(DateTime, nullable=True)

    # Account lockout
    locked_until = Column(DateTime, nullable=True)

    # Subscription (basic tracking - full subscription model separate)
    subscription_tier = Column(String(50), default='free', nullable=False)  # free, basic, pro, enterprise
    subscription_expires = Column(DateTime, nullable=True)

    # API usage tracking
    api_calls_today = Column(Integer, default=0, nullable=False)
    api_calls_reset_at = Column(DateTime, nullable=True)
    exports_this_month = Column(Integer, default=0, nullable=False)
    exports_reset_at = Column(DateTime, nullable=True)

    # Additional profile data
    profile_data = Column(JSON, nullable=True)  # Avatar URL, preferences, etc.

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
        Index('idx_user_reset_token', 'password_reset_token'),
        Index('idx_user_subscription', 'subscription_tier'),
        Index('idx_user_disabled', 'disabled'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in (self.roles or [])

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        user_roles = self.roles or []
        return any(role in user_roles for role in roles)

    def is_admin(self) -> bool:
        """Check if user is an admin"""
        return self.has_role("admin")

    def is_active(self) -> bool:
        """Check if user account is active (not disabled and not locked)"""
        if self.disabled:
            return False
        if self.locked_until and self.locked_until > datetime.utcnow():
            return False
        return True

    def can_access_feature(self, feature: str) -> bool:
        """
        Check if user's subscription tier allows access to a feature.
        """
        tier_features = {
            'free': ['basic_search', 'view_records'],
            'basic': ['basic_search', 'view_records', 'export_csv', 'advanced_search'],
            'pro': ['basic_search', 'view_records', 'export_csv', 'advanced_search',
                    'export_excel', 'bulk_operations', 'api_access'],
            'enterprise': ['basic_search', 'view_records', 'export_csv', 'advanced_search',
                          'export_excel', 'bulk_operations', 'api_access', 'unlimited_exports',
                          'priority_support', 'custom_integrations']
        }
        tier = self.subscription_tier or 'free'
        allowed_features = tier_features.get(tier, tier_features['free'])
        return feature in allowed_features

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary representation.

        Args:
            include_sensitive: If True, include sensitive fields like tokens

        Returns:
            Dictionary representation of user
        """
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'disabled': self.disabled,
            'email_verified': self.email_verified,
            'roles': self.roles,
            'subscription_tier': self.subscription_tier,
            'subscription_expires': self.subscription_expires.isoformat() if self.subscription_expires else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            result.update({
                'email_verification_token': self.email_verification_token,
                'password_reset_token': self.password_reset_token,
                'login_count': self.login_count,
                'failed_login_count': self.failed_login_count,
                'api_calls_today': self.api_calls_today,
                'exports_this_month': self.exports_this_month,
            })

        return result


# Database session management functions
def get_db():
    """Get database session"""
    return db_session()

def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def drop_tables():
    """Drop all database tables"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise

def reset_database():
    """Reset database by dropping and recreating all tables"""
    logger.info("Resetting database...")
    drop_tables()
    create_tables()
    logger.info("Database reset complete")

# Initialize database on import
try:
    create_tables()
except Exception as e:
    logger.warning(f"Could not create tables on import: {e}")
    logger.info("Tables may need to be created manually or database may not be available yet")
