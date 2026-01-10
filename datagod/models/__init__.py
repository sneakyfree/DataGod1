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

    # FIPS code support for standardized county identification
    fips_code = Column(String(5), nullable=True, index=True)  # Full 5-digit FIPS (state + county)
    state_fips = Column(String(2), nullable=True, index=True)  # 2-digit state FIPS
    county_fips = Column(String(3), nullable=True, index=True)  # 3-digit county FIPS
    county_seat = Column(String(100), nullable=True)  # County seat city name

    # Relationships
    data_sources = relationship("DataSource", back_populates="jurisdiction", cascade="all, delete-orphan")
    records = relationship("Record", back_populates="jurisdiction", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_jurisdiction_state_county', 'state', 'county'),
        Index('idx_jurisdiction_type', 'type'),
        Index('idx_jurisdiction_api_available', 'api_available'),
        Index('idx_jurisdiction_fips', 'fips_code'),
        Index('idx_jurisdiction_state_fips', 'state_fips'),
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


class SavedSearch(Base, TimestampMixin):
    """Represents a saved search for a user"""
    __tablename__ = 'saved_searches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Search details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Search parameters stored as JSON
    search_params = Column(JSON, nullable=False)  # query, filters, sort, etc.

    # Usage tracking
    last_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0, nullable=False)

    # Notification settings
    notify_on_new_results = Column(Boolean, default=False, nullable=False)
    notification_frequency = Column(String(50), default='daily')  # 'daily', 'weekly', 'immediate'
    last_notification = Column(DateTime, nullable=True)
    last_result_count = Column(Integer, default=0, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_saved_search_user', 'user_id'),
        Index('idx_saved_search_name', 'name'),
        Index('idx_saved_search_notify', 'notify_on_new_results'),
    )

    def __repr__(self):
        return f"<SavedSearch(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'search_params': self.search_params,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'run_count': self.run_count,
            'notify_on_new_results': self.notify_on_new_results,
            'notification_frequency': self.notification_frequency,
            'last_result_count': self.last_result_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserFavorite(Base, TimestampMixin):
    """Represents a user's favorited record or entity"""
    __tablename__ = 'user_favorites'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Can favorite either a record or an entity
    record_id = Column(Integer, ForeignKey('records.id'), nullable=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)

    # Type for quick filtering
    favorite_type = Column(String(50), nullable=False)  # 'record', 'entity'

    # User notes
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # User-defined tags

    # Indexes
    __table_args__ = (
        Index('idx_favorite_user', 'user_id'),
        Index('idx_favorite_record', 'record_id'),
        Index('idx_favorite_entity', 'entity_id'),
        Index('idx_favorite_type', 'favorite_type'),
    )

    def __repr__(self):
        return f"<UserFavorite(id={self.id}, user_id={self.user_id}, type='{self.favorite_type}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'record_id': self.record_id,
            'entity_id': self.entity_id,
            'favorite_type': self.favorite_type,
            'notes': self.notes,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserActivity(Base, TimestampMixin):
    """Tracks user activity for recent history and analytics"""
    __tablename__ = 'user_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # 'view_record', 'search', 'export', 'view_entity', etc.

    # Reference to what was accessed
    record_id = Column(Integer, ForeignKey('records.id'), nullable=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)
    search_id = Column(Integer, ForeignKey('saved_searches.id'), nullable=True)

    # Activity context
    activity_data = Column(JSON, nullable=True)  # Additional context (search query, export format, etc.)

    # Session info
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_activity_user', 'user_id'),
        Index('idx_activity_type', 'activity_type'),
        Index('idx_activity_created', 'created_at'),
        Index('idx_activity_record', 'record_id'),
        Index('idx_activity_entity', 'entity_id'),
    )

    def __repr__(self):
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, type='{self.activity_type}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'record_id': self.record_id,
            'entity_id': self.entity_id,
            'search_id': self.search_id,
            'activity_data': self.activity_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ShareLink(Base, TimestampMixin):
    """Represents a shareable link for records or entities"""
    __tablename__ = 'share_links'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Share token (unique identifier for the link)
    token = Column(String(64), unique=True, nullable=False, index=True)

    # What is being shared (record or entity)
    record_id = Column(Integer, ForeignKey('records.id'), nullable=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)
    share_type = Column(String(20), nullable=False)  # 'record' or 'entity'

    # Optional message from sharer
    message = Column(Text, nullable=True)

    # Expiration settings
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Access tracking
    view_count = Column(Integer, default=0, nullable=False)
    last_viewed = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_share_token', 'token'),
        Index('idx_share_user', 'user_id'),
        Index('idx_share_record', 'record_id'),
        Index('idx_share_entity', 'entity_id'),
        Index('idx_share_active', 'is_active'),
    )

    def __repr__(self):
        return f"<ShareLink(id={self.id}, token='{self.token[:8]}...', type='{self.share_type}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'token': self.token,
            'share_type': self.share_type,
            'record_id': self.record_id,
            'entity_id': self.entity_id,
            'message': self.message,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'view_count': self.view_count,
            'last_viewed': self.last_viewed.isoformat() if self.last_viewed else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


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

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)

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
