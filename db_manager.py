"""
DataGod Database Manager
Provides high-level database operations for the DataGod platform.
"""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, or_, and_, func, desc, asc
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.pool import QueuePool

from datagod.config.settings import (
    DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT, DB_POOL_RECYCLE
)
from datagod.models import (
    Base, Jurisdiction, DataSource, Record, Entity, Relationship, User
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    High-level database manager for DataGod operations.
    Provides CRUD operations for all models and advanced query capabilities.
    """

    def __init__(self, database_url: str = None):
        """
        Initialize the DatabaseManager.

        Args:
            database_url: Optional database URL. Uses default from settings if not provided.
        """
        self.database_url = database_url or DATABASE_URL

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_recycle=DB_POOL_RECYCLE,
            echo=False
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Create scoped session for thread safety
        self.scoped_session = scoped_session(self.SessionLocal)

        logger.info(f"DatabaseManager initialized with {self.database_url}")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        Automatically handles commits and rollbacks.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def init_database(self) -> bool:
        """
        Initialize the database by creating all tables.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            return False

    def drop_all_tables(self) -> bool:
        """
        Drop all database tables. USE WITH CAUTION!

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("All database tables dropped")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {e}")
            return False

    def reset_database(self) -> bool:
        """
        Reset the database by dropping and recreating all tables.

        Returns:
            bool: True if successful, False otherwise.
        """
        logger.warning("Resetting database - all data will be lost!")
        if self.drop_all_tables():
            return self.init_database()
        return False

    # ==================== JURISDICTION OPERATIONS ====================

    def create_jurisdiction(
        self,
        name: str,
        state: str = None,
        county: str = None,
        jurisdiction_type: str = None,
        api_available: bool = False,
        scraper_needed: bool = True,
        population: int = None,
        area_sq_miles: float = None,
        description: str = None,
        contact_info: Dict = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """
        Create a new jurisdiction.

        Returns:
            int: The ID of the created jurisdiction, or None if failed.
        """
        try:
            with self.get_session() as session:
                jurisdiction = Jurisdiction(
                    name=name,
                    state=state,
                    county=county,
                    type=jurisdiction_type,
                    api_available=api_available,
                    scraper_needed=scraper_needed,
                    population=population,
                    area_sq_miles=area_sq_miles,
                    description=description,
                    contact_info=contact_info,
                    jurisdiction_metadata=metadata
                )
                session.add(jurisdiction)
                session.flush()
                jurisdiction_id = jurisdiction.id
                logger.info(f"Created jurisdiction: {name} (ID: {jurisdiction_id})")
                return jurisdiction_id
        except IntegrityError:
            logger.error(f"Jurisdiction '{name}' already exists")
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error creating jurisdiction: {e}")
            return None

    def get_jurisdiction(self, jurisdiction_id: int) -> Optional[Dict[str, Any]]:
        """Get a jurisdiction by ID."""
        try:
            with self.get_session() as session:
                jurisdiction = session.query(Jurisdiction).filter_by(id=jurisdiction_id).first()
                if jurisdiction:
                    return self._jurisdiction_to_dict(jurisdiction)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting jurisdiction: {e}")
            return None

    def get_jurisdiction_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a jurisdiction by name."""
        try:
            with self.get_session() as session:
                jurisdiction = session.query(Jurisdiction).filter_by(name=name).first()
                if jurisdiction:
                    return self._jurisdiction_to_dict(jurisdiction)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting jurisdiction by name: {e}")
            return None

    def list_jurisdictions(
        self,
        state: str = None,
        county: str = None,
        jurisdiction_type: str = None,
        api_available: bool = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "name",
        order_desc: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List jurisdictions with optional filtering.

        Returns:
            List of jurisdiction dictionaries.
        """
        try:
            with self.get_session() as session:
                query = session.query(Jurisdiction)

                # Apply filters
                if state:
                    query = query.filter(Jurisdiction.state == state)
                if county:
                    query = query.filter(Jurisdiction.county == county)
                if jurisdiction_type:
                    query = query.filter(Jurisdiction.type == jurisdiction_type)
                if api_available is not None:
                    query = query.filter(Jurisdiction.api_available == api_available)

                # Apply ordering
                order_column = getattr(Jurisdiction, order_by, Jurisdiction.name)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

                # Apply pagination
                jurisdictions = query.offset(offset).limit(limit).all()

                return [self._jurisdiction_to_dict(j) for j in jurisdictions]
        except SQLAlchemyError as e:
            logger.error(f"Error listing jurisdictions: {e}")
            return []

    def update_jurisdiction(
        self,
        jurisdiction_id: int,
        **kwargs
    ) -> bool:
        """Update a jurisdiction with the provided fields."""
        try:
            with self.get_session() as session:
                jurisdiction = session.query(Jurisdiction).filter_by(id=jurisdiction_id).first()
                if not jurisdiction:
                    logger.warning(f"Jurisdiction {jurisdiction_id} not found")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'name', 'state', 'county', 'type', 'api_available',
                    'scraper_needed', 'population', 'area_sq_miles',
                    'description', 'contact_info', 'jurisdiction_metadata'
                ]
                for key, value in kwargs.items():
                    if key in allowed_fields and value is not None:
                        setattr(jurisdiction, key, value)

                jurisdiction.updated_at = datetime.utcnow()
                logger.info(f"Updated jurisdiction: {jurisdiction_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating jurisdiction: {e}")
            return False

    def delete_jurisdiction(self, jurisdiction_id: int) -> bool:
        """Delete a jurisdiction by ID."""
        try:
            with self.get_session() as session:
                jurisdiction = session.query(Jurisdiction).filter_by(id=jurisdiction_id).first()
                if not jurisdiction:
                    logger.warning(f"Jurisdiction {jurisdiction_id} not found")
                    return False

                session.delete(jurisdiction)
                logger.info(f"Deleted jurisdiction: {jurisdiction_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting jurisdiction: {e}")
            return False

    def count_jurisdictions(self, state: str = None) -> int:
        """Count jurisdictions, optionally filtered by state."""
        try:
            with self.get_session() as session:
                query = session.query(func.count(Jurisdiction.id))
                if state:
                    query = query.filter(Jurisdiction.state == state)
                return query.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting jurisdictions: {e}")
            return 0

    # ==================== DATA SOURCE OPERATIONS ====================

    def create_data_source(
        self,
        jurisdiction_id: int,
        source_name: str,
        source_type: str,
        api_endpoint: str = None,
        api_key: str = None,
        status: str = "active",
        scrape_interval_hours: int = 24,
        description: str = None,
        config: Dict = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """Create a new data source."""
        try:
            with self.get_session() as session:
                # Verify jurisdiction exists
                jurisdiction = session.query(Jurisdiction).filter_by(id=jurisdiction_id).first()
                if not jurisdiction:
                    logger.error(f"Jurisdiction {jurisdiction_id} not found")
                    return None

                data_source = DataSource(
                    jurisdiction_id=jurisdiction_id,
                    source_name=source_name,
                    source_type=source_type,
                    api_endpoint=api_endpoint,
                    api_key=api_key,
                    status=status,
                    scrape_interval_hours=scrape_interval_hours,
                    description=description,
                    config=config,
                    source_metadata=metadata
                )
                session.add(data_source)
                session.flush()
                source_id = data_source.id
                logger.info(f"Created data source: {source_name} (ID: {source_id})")
                return source_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating data source: {e}")
            return None

    def get_data_source(self, data_source_id: int) -> Optional[Dict[str, Any]]:
        """Get a data source by ID."""
        try:
            with self.get_session() as session:
                data_source = session.query(DataSource).filter_by(id=data_source_id).first()
                if data_source:
                    return self._data_source_to_dict(data_source)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting data source: {e}")
            return None

    def list_data_sources(
        self,
        jurisdiction_id: int = None,
        source_type: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List data sources with optional filtering."""
        try:
            with self.get_session() as session:
                query = session.query(DataSource)

                if jurisdiction_id:
                    query = query.filter(DataSource.jurisdiction_id == jurisdiction_id)
                if source_type:
                    query = query.filter(DataSource.source_type == source_type)
                if status:
                    query = query.filter(DataSource.status == status)

                data_sources = query.offset(offset).limit(limit).all()
                return [self._data_source_to_dict(ds) for ds in data_sources]
        except SQLAlchemyError as e:
            logger.error(f"Error listing data sources: {e}")
            return []

    def update_data_source_status(
        self,
        data_source_id: int,
        status: str,
        error_count: int = None,
        success_count: int = None
    ) -> bool:
        """Update a data source status."""
        try:
            with self.get_session() as session:
                data_source = session.query(DataSource).filter_by(id=data_source_id).first()
                if not data_source:
                    return False

                data_source.status = status
                if error_count is not None:
                    data_source.error_count = error_count
                if success_count is not None:
                    data_source.success_count = success_count
                data_source.updated_at = datetime.utcnow()

                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating data source status: {e}")
            return False

    def record_scrape(
        self,
        data_source_id: int,
        success: bool = True
    ) -> bool:
        """Record a scrape attempt for a data source."""
        try:
            with self.get_session() as session:
                data_source = session.query(DataSource).filter_by(id=data_source_id).first()
                if not data_source:
                    return False

                data_source.last_scraped = datetime.utcnow()
                if success:
                    data_source.success_count = (data_source.success_count or 0) + 1
                    data_source.status = "active"
                else:
                    data_source.error_count = (data_source.error_count or 0) + 1
                    if data_source.error_count >= 3:
                        data_source.status = "error"

                return True
        except SQLAlchemyError as e:
            logger.error(f"Error recording scrape: {e}")
            return False

    # ==================== RECORD OPERATIONS ====================

    def create_record(
        self,
        jurisdiction_id: int,
        data_source_id: int,
        record_type: str,
        title: str,
        description: str = None,
        amount: float = None,
        date: datetime = None,
        address: str = None,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        grantor: str = None,
        grantee: str = None,
        borrower: str = None,
        lender: str = None,
        document_number: str = None,
        url: str = None,
        raw_data: Dict = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """Create a new record."""
        try:
            with self.get_session() as session:
                record = Record(
                    jurisdiction_id=jurisdiction_id,
                    data_source_id=data_source_id,
                    record_type=record_type,
                    title=title,
                    description=description,
                    amount=amount,
                    date=date,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    grantor=grantor,
                    grantee=grantee,
                    borrower=borrower,
                    lender=lender,
                    document_number=document_number,
                    url=url,
                    raw_data=raw_data,
                    record_metadata=metadata
                )
                session.add(record)
                session.flush()
                record_id = record.id
                logger.debug(f"Created record: {title[:50]} (ID: {record_id})")
                return record_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating record: {e}")
            return None

    def bulk_create_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Bulk create records for better performance.

        Args:
            records: List of record dictionaries.

        Returns:
            Number of records created.
        """
        created_count = 0
        try:
            with self.get_session() as session:
                for record_data in records:
                    record = Record(**record_data)
                    session.add(record)
                    created_count += 1

                logger.info(f"Bulk created {created_count} records")
                return created_count
        except SQLAlchemyError as e:
            logger.error(f"Error bulk creating records: {e}")
            return 0

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Get a record by ID."""
        try:
            with self.get_session() as session:
                record = session.query(Record).filter_by(id=record_id).first()
                if record:
                    return self._record_to_dict(record)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting record: {e}")
            return None

    def search_records(
        self,
        query: str = None,
        jurisdiction_id: int = None,
        record_type: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        amount_min: float = None,
        amount_max: float = None,
        grantor: str = None,
        grantee: str = None,
        city: str = None,
        state: str = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "date",
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search records with comprehensive filtering.

        Returns:
            List of matching records.
        """
        try:
            with self.get_session() as session:
                db_query = session.query(Record)

                # Text search
                if query:
                    search_filter = or_(
                        Record.title.ilike(f"%{query}%"),
                        Record.description.ilike(f"%{query}%"),
                        Record.grantor.ilike(f"%{query}%"),
                        Record.grantee.ilike(f"%{query}%"),
                        Record.address.ilike(f"%{query}%")
                    )
                    db_query = db_query.filter(search_filter)

                # Apply filters
                if jurisdiction_id:
                    db_query = db_query.filter(Record.jurisdiction_id == jurisdiction_id)
                if record_type:
                    db_query = db_query.filter(Record.record_type == record_type)
                if date_from:
                    db_query = db_query.filter(Record.date >= date_from)
                if date_to:
                    db_query = db_query.filter(Record.date <= date_to)
                if amount_min:
                    db_query = db_query.filter(Record.amount >= amount_min)
                if amount_max:
                    db_query = db_query.filter(Record.amount <= amount_max)
                if grantor:
                    db_query = db_query.filter(Record.grantor.ilike(f"%{grantor}%"))
                if grantee:
                    db_query = db_query.filter(Record.grantee.ilike(f"%{grantee}%"))
                if city:
                    db_query = db_query.filter(Record.city == city)
                if state:
                    db_query = db_query.filter(Record.state == state)

                # Filter out non-active records
                db_query = db_query.filter(Record.status == "active")

                # Apply ordering
                order_column = getattr(Record, order_by, Record.date)
                if order_desc:
                    db_query = db_query.order_by(desc(order_column))
                else:
                    db_query = db_query.order_by(asc(order_column))

                # Apply pagination
                records = db_query.offset(offset).limit(limit).all()

                return [self._record_to_dict(r) for r in records]
        except SQLAlchemyError as e:
            logger.error(f"Error searching records: {e}")
            return []

    def count_records(
        self,
        jurisdiction_id: int = None,
        record_type: str = None,
        status: str = "active"
    ) -> int:
        """Count records with optional filtering."""
        try:
            with self.get_session() as session:
                query = session.query(func.count(Record.id))

                if jurisdiction_id:
                    query = query.filter(Record.jurisdiction_id == jurisdiction_id)
                if record_type:
                    query = query.filter(Record.record_type == record_type)
                if status:
                    query = query.filter(Record.status == status)

                return query.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting records: {e}")
            return 0

    def get_record_stats(self) -> Dict[str, Any]:
        """Get overall record statistics."""
        try:
            with self.get_session() as session:
                total = session.query(func.count(Record.id)).scalar() or 0
                by_type = session.query(
                    Record.record_type,
                    func.count(Record.id)
                ).group_by(Record.record_type).all()

                total_amount = session.query(func.sum(Record.amount)).scalar() or 0
                avg_amount = session.query(func.avg(Record.amount)).scalar() or 0

                return {
                    "total_records": total,
                    "by_type": {t: c for t, c in by_type},
                    "total_amount": float(total_amount),
                    "average_amount": float(avg_amount)
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting record stats: {e}")
            return {}

    # ==================== ENTITY OPERATIONS ====================

    def create_entity(
        self,
        entity_name: str,
        entity_type: str,
        entity_id: str = None,
        address: str = None,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        phone: str = None,
        email: str = None,
        description: str = None,
        data: Dict = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """Create a new entity."""
        try:
            with self.get_session() as session:
                entity = Entity(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=phone,
                    email=email,
                    description=description,
                    data=data,
                    entity_metadata=metadata
                )
                session.add(entity)
                session.flush()
                new_id = entity.id
                logger.info(f"Created entity: {entity_name} (ID: {new_id})")
                return new_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating entity: {e}")
            return None

    def get_entity(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get an entity by ID."""
        try:
            with self.get_session() as session:
                entity = session.query(Entity).filter_by(id=entity_id).first()
                if entity:
                    return self._entity_to_dict(entity)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting entity: {e}")
            return None

    def search_entities(
        self,
        query: str = None,
        entity_type: str = None,
        city: str = None,
        state: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search entities."""
        try:
            with self.get_session() as session:
                db_query = session.query(Entity)

                if query:
                    db_query = db_query.filter(
                        Entity.entity_name.ilike(f"%{query}%")
                    )
                if entity_type:
                    db_query = db_query.filter(Entity.entity_type == entity_type)
                if city:
                    db_query = db_query.filter(Entity.city == city)
                if state:
                    db_query = db_query.filter(Entity.state == state)

                entities = db_query.offset(offset).limit(limit).all()
                return [self._entity_to_dict(e) for e in entities]
        except SQLAlchemyError as e:
            logger.error(f"Error searching entities: {e}")
            return []

    # ==================== RELATIONSHIP OPERATIONS ====================

    def create_relationship(
        self,
        entity1_id: int,
        entity2_id: int,
        record_id: int,
        relationship_type: str,
        role1: str = None,
        role2: str = None,
        context: str = None,
        confidence_score: float = 1.0,
        evidence: Dict = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """Create a new relationship between entities."""
        try:
            with self.get_session() as session:
                relationship = Relationship(
                    entity1_id=entity1_id,
                    entity2_id=entity2_id,
                    record_id=record_id,
                    relationship_type=relationship_type,
                    role1=role1,
                    role2=role2,
                    context=context,
                    confidence_score=confidence_score,
                    evidence=evidence,
                    relationship_metadata=metadata
                )
                session.add(relationship)
                session.flush()
                new_id = relationship.id
                logger.info(f"Created relationship: {entity1_id} <-> {entity2_id} (ID: {new_id})")
                return new_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating relationship: {e}")
            return None

    def get_entity_relationships(
        self,
        entity_id: int,
        relationship_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        try:
            with self.get_session() as session:
                query = session.query(Relationship).filter(
                    or_(
                        Relationship.entity1_id == entity_id,
                        Relationship.entity2_id == entity_id
                    )
                )

                if relationship_type:
                    query = query.filter(Relationship.relationship_type == relationship_type)

                relationships = query.all()
                return [self._relationship_to_dict(r) for r in relationships]
        except SQLAlchemyError as e:
            logger.error(f"Error getting entity relationships: {e}")
            return []

    # ==================== DASHBOARD / STATS ====================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        try:
            with self.get_session() as session:
                total_records = session.query(func.count(Record.id)).scalar() or 0
                total_jurisdictions = session.query(func.count(Jurisdiction.id)).scalar() or 0
                total_data_sources = session.query(func.count(DataSource.id)).scalar() or 0
                active_scrapers = session.query(func.count(DataSource.id)).filter(
                    DataSource.status == "active"
                ).scalar() or 0
                total_entities = session.query(func.count(Entity.id)).scalar() or 0

                # Get recent records
                recent_records = session.query(Record).order_by(
                    desc(Record.created_at)
                ).limit(10).all()

                return {
                    "totalRecords": total_records,
                    "jurisdictions": total_jurisdictions,
                    "dataSources": total_data_sources,
                    "activeScrapers": active_scrapers,
                    "totalEntities": total_entities,
                    "recentRecords": [self._record_to_dict(r) for r in recent_records]
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                "totalRecords": 0,
                "jurisdictions": 0,
                "dataSources": 0,
                "activeScrapers": 0,
                "totalEntities": 0,
                "recentRecords": []
            }

    # ==================== USER OPERATIONS ====================

    def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: str = None,
        roles: List[str] = None,
        disabled: bool = False,
        email_verified: bool = False,
        subscription_tier: str = 'free'
    ) -> Optional[int]:
        """
        Create a new user.

        Args:
            username: Unique username
            email: Unique email address
            hashed_password: Already hashed password
            full_name: Optional full name
            roles: List of roles (default: ['user'])
            disabled: Whether user is disabled
            email_verified: Whether email is verified
            subscription_tier: Subscription tier (default: 'free')

        Returns:
            int: The ID of the created user, or None if failed.
        """
        try:
            with self.get_session() as session:
                user = User(
                    username=username,
                    email=email,
                    hashed_password=hashed_password,
                    full_name=full_name,
                    roles=roles or ['user'],
                    disabled=disabled,
                    email_verified=email_verified,
                    subscription_tier=subscription_tier
                )
                session.add(user)
                session.flush()
                user_id = user.id
                logger.info(f"Created user: {username} (ID: {user_id})")
                return user_id
        except IntegrityError as e:
            logger.error(f"User '{username}' or email '{email}' already exists: {e}")
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if user:
                    return self._user_to_dict(user)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a user by username."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if user:
                    return self._user_to_dict(user)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(email=email).first()
                if user:
                    return self._user_to_dict(user)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_user_for_auth(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username with hashed_password included (for authentication).
        Returns a dictionary with hashed_password field included.
        """
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if user:
                    return self._user_to_dict_with_password(user)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user for auth: {e}")
            return None

    def check_user_locked(self, username: str) -> bool:
        """Check if a user account is locked."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False
                if user.locked_until and user.locked_until > datetime.utcnow():
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error checking user lock status: {e}")
            return False

    def list_users(
        self,
        disabled: bool = None,
        subscription_tier: str = None,
        role: str = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List users with optional filtering.

        Returns:
            List of user dictionaries (without hashed_password).
        """
        try:
            with self.get_session() as session:
                query = session.query(User)

                # Apply filters
                if disabled is not None:
                    query = query.filter(User.disabled == disabled)
                if subscription_tier:
                    query = query.filter(User.subscription_tier == subscription_tier)
                # Note: Filtering by role requires JSON contains query
                # This is database-specific; for now, we'll filter in Python

                # Apply ordering
                order_column = getattr(User, order_by, User.created_at)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

                # Apply pagination
                users = query.offset(offset).limit(limit).all()

                # Filter by role if specified (post-query filtering for JSON)
                if role:
                    users = [u for u in users if role in (u.roles or [])]

                return [self._user_to_dict(u) for u in users]
        except SQLAlchemyError as e:
            logger.error(f"Error listing users: {e}")
            return []

    def update_user(
        self,
        user_id: int,
        **kwargs
    ) -> bool:
        """Update a user with the provided fields."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'email', 'hashed_password', 'full_name', 'disabled',
                    'email_verified', 'roles', 'email_verification_token',
                    'email_verification_expires', 'password_reset_token',
                    'password_reset_expires', 'last_login', 'login_count',
                    'failed_login_count', 'last_failed_login', 'locked_until',
                    'subscription_tier', 'subscription_expires', 'api_calls_today',
                    'api_calls_reset_at', 'exports_this_month', 'exports_reset_at',
                    'profile_data'
                ]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        setattr(user, key, value)

                user.updated_at = datetime.utcnow()
                logger.info(f"Updated user: {user_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating user: {e}")
            return False

    def update_user_by_username(
        self,
        username: str,
        **kwargs
    ) -> bool:
        """Update a user by username with the provided fields."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    logger.warning(f"User '{username}' not found")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'email', 'hashed_password', 'full_name', 'disabled',
                    'email_verified', 'roles', 'email_verification_token',
                    'email_verification_expires', 'password_reset_token',
                    'password_reset_expires', 'last_login', 'login_count',
                    'failed_login_count', 'last_failed_login', 'locked_until',
                    'subscription_tier', 'subscription_expires', 'api_calls_today',
                    'api_calls_reset_at', 'exports_this_month', 'exports_reset_at',
                    'profile_data'
                ]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        setattr(user, key, value)

                user.updated_at = datetime.utcnow()
                logger.info(f"Updated user: {username}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return False

                session.delete(user)
                logger.info(f"Deleted user: {user_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def delete_user_by_username(self, username: str) -> bool:
        """Delete a user by username."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    logger.warning(f"User '{username}' not found")
                    return False

                session.delete(user)
                logger.info(f"Deleted user: {username}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def count_users(self, disabled: bool = None, subscription_tier: str = None) -> int:
        """Count users with optional filtering."""
        try:
            with self.get_session() as session:
                query = session.query(func.count(User.id))
                if disabled is not None:
                    query = query.filter(User.disabled == disabled)
                if subscription_tier:
                    query = query.filter(User.subscription_tier == subscription_tier)
                return query.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting users: {e}")
            return 0

    def record_login(self, username: str, success: bool = True) -> bool:
        """Record a login attempt for a user."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False

                if success:
                    user.last_login = datetime.utcnow()
                    user.login_count = (user.login_count or 0) + 1
                    user.failed_login_count = 0  # Reset on successful login
                    user.locked_until = None  # Unlock on successful login
                else:
                    user.failed_login_count = (user.failed_login_count or 0) + 1
                    user.last_failed_login = datetime.utcnow()

                    # Lock account after 5 failed attempts
                    if user.failed_login_count >= 5:
                        from datetime import timedelta
                        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                        logger.warning(f"User {username} locked due to failed login attempts")

                return True
        except SQLAlchemyError as e:
            logger.error(f"Error recording login: {e}")
            return False

    def set_password_reset_token(self, email: str, token: str, expires_hours: int = 1) -> bool:
        """Set a password reset token for a user."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(email=email).first()
                if not user:
                    return False

                from datetime import timedelta
                user.password_reset_token = token
                user.password_reset_expires = datetime.utcnow() + timedelta(hours=expires_hours)
                logger.info(f"Set password reset token for user: {email}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error setting password reset token: {e}")
            return False

    def get_user_by_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get a user by password reset token (if valid and not expired)."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(
                    User.password_reset_token == token,
                    User.password_reset_expires > datetime.utcnow()
                ).first()
                if user:
                    return self._user_to_dict(user)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by reset token: {e}")
            return None

    def clear_password_reset_token(self, user_id: int) -> bool:
        """Clear the password reset token for a user."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return False

                user.password_reset_token = None
                user.password_reset_expires = None
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error clearing password reset token: {e}")
            return False

    def increment_api_calls(self, user_id: int) -> bool:
        """Increment API call count for a user (for rate limiting)."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return False

                # Reset count if it's a new day
                now = datetime.utcnow()
                if user.api_calls_reset_at is None or user.api_calls_reset_at.date() < now.date():
                    user.api_calls_today = 1
                    user.api_calls_reset_at = now
                else:
                    user.api_calls_today = (user.api_calls_today or 0) + 1

                return True
        except SQLAlchemyError as e:
            logger.error(f"Error incrementing API calls: {e}")
            return False

    def increment_exports(self, user_id: int) -> bool:
        """Increment export count for a user."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return False

                # Reset count if it's a new month
                now = datetime.utcnow()
                if user.exports_reset_at is None or (
                    user.exports_reset_at.year < now.year or
                    user.exports_reset_at.month < now.month
                ):
                    user.exports_this_month = 1
                    user.exports_reset_at = now
                else:
                    user.exports_this_month = (user.exports_this_month or 0) + 1

                return True
        except SQLAlchemyError as e:
            logger.error(f"Error incrementing exports: {e}")
            return False

    # ==================== HELPER METHODS ====================

    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """Convert User model to dictionary (excludes sensitive data like hashed_password)."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "email_verified": user.email_verified,
            "roles": user.roles or ['user'],
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "login_count": user.login_count or 0,
            "subscription_tier": user.subscription_tier or 'free',
            "subscription_expires": user.subscription_expires.isoformat() if user.subscription_expires else None,
            "api_calls_today": user.api_calls_today or 0,
            "exports_this_month": user.exports_this_month or 0,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

    def _user_to_dict_with_password(self, user: User) -> Dict[str, Any]:
        """Convert User model to dictionary (includes hashed_password for auth)."""
        result = self._user_to_dict(user)
        result["hashed_password"] = user.hashed_password
        return result

    def _jurisdiction_to_dict(self, jurisdiction: Jurisdiction) -> Dict[str, Any]:
        """Convert Jurisdiction model to dictionary."""
        return {
            "id": jurisdiction.id,
            "name": jurisdiction.name,
            "state": jurisdiction.state,
            "county": jurisdiction.county,
            "type": jurisdiction.type,
            "api_available": jurisdiction.api_available,
            "scraper_needed": jurisdiction.scraper_needed,
            "population": jurisdiction.population,
            "area_sq_miles": jurisdiction.area_sq_miles,
            "description": jurisdiction.description,
            "contact_info": jurisdiction.contact_info,
            "metadata": jurisdiction.jurisdiction_metadata,
            "created_at": jurisdiction.created_at.isoformat() if jurisdiction.created_at else None,
            "updated_at": jurisdiction.updated_at.isoformat() if jurisdiction.updated_at else None
        }

    def _data_source_to_dict(self, data_source: DataSource) -> Dict[str, Any]:
        """Convert DataSource model to dictionary."""
        return {
            "id": data_source.id,
            "jurisdiction_id": data_source.jurisdiction_id,
            "source_name": data_source.source_name,
            "source_type": data_source.source_type,
            "api_endpoint": data_source.api_endpoint,
            "status": data_source.status,
            "last_scraped": data_source.last_scraped.isoformat() if data_source.last_scraped else None,
            "scrape_interval_hours": data_source.scrape_interval_hours,
            "error_count": data_source.error_count,
            "success_count": data_source.success_count,
            "description": data_source.description,
            "config": data_source.config,
            "metadata": data_source.source_metadata,
            "created_at": data_source.created_at.isoformat() if data_source.created_at else None,
            "updated_at": data_source.updated_at.isoformat() if data_source.updated_at else None
        }

    def _record_to_dict(self, record: Record) -> Dict[str, Any]:
        """Convert Record model to dictionary."""
        return {
            "id": record.id,
            "jurisdiction_id": record.jurisdiction_id,
            "data_source_id": record.data_source_id,
            "record_id": record.record_id,
            "record_type": record.record_type,
            "title": record.title,
            "description": record.description,
            "amount": record.amount,
            "date": record.date.isoformat() if record.date else None,
            "address": record.address,
            "city": record.city,
            "state": record.state,
            "zip_code": record.zip_code,
            "grantor": record.grantor,
            "grantee": record.grantee,
            "borrower": record.borrower,
            "lender": record.lender,
            "document_number": record.document_number,
            "url": record.url,
            "status": record.status,
            "quality_score": record.quality_score,
            "metadata": record.record_metadata,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }

    def _entity_to_dict(self, entity: Entity) -> Dict[str, Any]:
        """Convert Entity model to dictionary."""
        return {
            "id": entity.id,
            "entity_name": entity.entity_name,
            "entity_type": entity.entity_type,
            "entity_id": entity.entity_id,
            "address": entity.address,
            "city": entity.city,
            "state": entity.state,
            "zip_code": entity.zip_code,
            "phone": entity.phone,
            "email": entity.email,
            "status": entity.status,
            "description": entity.description,
            "data": entity.data,
            "metadata": entity.entity_metadata,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None
        }

    def _relationship_to_dict(self, relationship: Relationship) -> Dict[str, Any]:
        """Convert Relationship model to dictionary."""
        return {
            "id": relationship.id,
            "entity1_id": relationship.entity1_id,
            "entity2_id": relationship.entity2_id,
            "record_id": relationship.record_id,
            "relationship_type": relationship.relationship_type,
            "role1": relationship.role1,
            "role2": relationship.role2,
            "context": relationship.context,
            "confidence_score": relationship.confidence_score,
            "evidence": relationship.evidence,
            "status": relationship.status,
            "metadata": relationship.relationship_metadata,
            "created_at": relationship.created_at.isoformat() if relationship.created_at else None,
            "updated_at": relationship.updated_at.isoformat() if relationship.updated_at else None
        }


# Create a global instance for convenience
db_manager = DatabaseManager()


# Convenience functions
def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def init_db():
    """Initialize the database."""
    return db_manager.init_database()


def get_session():
    """Get a database session."""
    return db_manager.get_session()
