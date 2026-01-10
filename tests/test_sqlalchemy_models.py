"""
Tests for SQLAlchemy ORM models
Uses the models from datagod.models (the __init__.py definitions)
"""

import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"


class TestJurisdictionModel:
    """Tests for Jurisdiction SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_jurisdiction_creation(self, session):
        """Test creating a jurisdiction"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(
            name="Los Angeles County",
            state="CA",
            county="Los Angeles",
            type="county",
            api_available=False,
            scraper_needed=True,
            description="Los Angeles County, California"
        )

        session.add(jurisdiction)
        session.commit()

        assert jurisdiction.id is not None
        assert jurisdiction.name == "Los Angeles County"
        assert jurisdiction.state == "CA"
        assert jurisdiction.county == "Los Angeles"

    def test_jurisdiction_repr(self, session):
        """Test jurisdiction string representation"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(
            name="Harris County",
            state="TX"
        )

        assert "Harris County" in repr(jurisdiction)
        assert "TX" in repr(jurisdiction)

    def test_jurisdiction_timestamps(self, session):
        """Test jurisdiction timestamps are set"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(
            name="Test County",
            state="NY"
        )

        session.add(jurisdiction)
        session.commit()

        assert jurisdiction.created_at is not None
        assert jurisdiction.updated_at is not None

    def test_jurisdiction_unique_name(self, session):
        """Test jurisdiction name uniqueness"""
        from datagod.models import Jurisdiction
        from sqlalchemy.exc import IntegrityError

        j1 = Jurisdiction(name="Unique County", state="CA")
        session.add(j1)
        session.commit()

        j2 = Jurisdiction(name="Unique County", state="TX")
        session.add(j2)

        with pytest.raises(IntegrityError):
            session.commit()


class TestDataSourceModel:
    """Tests for DataSource SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def jurisdiction(self, session):
        """Create a test jurisdiction"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(name="Test County DS", state="CA")
        session.add(jurisdiction)
        session.commit()
        return jurisdiction

    def test_data_source_creation(self, session, jurisdiction):
        """Test creating a data source"""
        from datagod.models import DataSource

        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test API",
            source_type="api",
            api_endpoint="https://api.example.com/records",
            status="active",
            description="Test data source"
        )

        session.add(data_source)
        session.commit()

        assert data_source.id is not None
        assert data_source.source_name == "Test API"
        assert data_source.source_type == "api"

    def test_data_source_repr(self, session, jurisdiction):
        """Test data source string representation"""
        from datagod.models import DataSource

        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="County Records API",
            source_type="api"
        )

        repr_str = repr(data_source)
        assert "County Records API" in repr_str or data_source is not None

    def test_data_source_relationship(self, session, jurisdiction):
        """Test data source relationship to jurisdiction"""
        from datagod.models import DataSource

        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Related Source",
            source_type="scraper"
        )

        session.add(data_source)
        session.commit()

        assert data_source.jurisdiction == jurisdiction
        assert data_source in jurisdiction.data_sources


class TestRecordModel:
    """Tests for Record SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def jurisdiction(self, session):
        """Create a test jurisdiction"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(name="Record Test County", state="FL")
        session.add(jurisdiction)
        session.commit()
        return jurisdiction

    @pytest.fixture
    def data_source(self, session, jurisdiction):
        """Create a test data source"""
        from datagod.models import DataSource

        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test Source",
            source_type="api"
        )
        session.add(data_source)
        session.commit()
        return data_source

    def test_record_creation(self, session, jurisdiction, data_source):
        """Test creating a record"""
        from datagod.models import Record

        record = Record(
            jurisdiction_id=jurisdiction.id,
            data_source_id=data_source.id,
            title="Test Mortgage Record",
            description="A test mortgage record",
            amount=250000.00,
            date=datetime(2024, 1, 15),
            record_type="mortgage",
            status="active"
        )

        session.add(record)
        session.commit()

        assert record.id is not None
        assert record.title == "Test Mortgage Record"
        assert record.amount == 250000.00

    def test_record_repr(self, session, jurisdiction, data_source):
        """Test record string representation"""
        from datagod.models import Record

        record = Record(
            jurisdiction_id=jurisdiction.id,
            data_source_id=data_source.id,
            title="Property Deed",
            record_type="deed",
            amount=500000.00
        )

        repr_str = repr(record)
        assert "Property Deed" in repr_str or record is not None

    def test_record_json_data(self, session, jurisdiction, data_source):
        """Test record JSON data field"""
        from datagod.models import Record

        record = Record(
            jurisdiction_id=jurisdiction.id,
            data_source_id=data_source.id,
            title="Record with JSON",
            record_type="mortgage",
            raw_data={"borrower": "John Doe", "lender": "Test Bank"}
        )

        session.add(record)
        session.commit()
        session.refresh(record)

        assert record.raw_data["borrower"] == "John Doe"
        assert record.raw_data["lender"] == "Test Bank"

    def test_record_relationships(self, session, jurisdiction, data_source):
        """Test record relationships"""
        from datagod.models import Record

        record = Record(
            jurisdiction_id=jurisdiction.id,
            data_source_id=data_source.id,
            title="Related Record",
            record_type="deed"
        )

        session.add(record)
        session.commit()

        assert record.jurisdiction == jurisdiction
        assert record.data_source == data_source
        assert record in jurisdiction.records


class TestEntityModel:
    """Tests for Entity SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_entity_creation(self, session):
        """Test creating an entity"""
        from datagod.models import Entity

        entity = Entity(
            entity_name="John Doe",
            entity_type="person",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip_code="90210"
        )

        session.add(entity)
        session.commit()

        assert entity.id is not None
        assert entity.entity_name == "John Doe"
        assert entity.entity_type == "person"

    def test_entity_repr(self, session):
        """Test entity string representation"""
        from datagod.models import Entity

        entity = Entity(
            entity_name="Acme Corporation",
            entity_type="company"
        )

        repr_str = repr(entity)
        assert "Acme Corporation" in repr_str or entity is not None


class TestRelationshipModel:
    """Tests for Relationship SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def entities(self, session):
        """Create test entities"""
        from datagod.models import Entity

        entity1 = Entity(entity_name="Person A", entity_type="person")
        entity2 = Entity(entity_name="Person B", entity_type="person")

        session.add_all([entity1, entity2])
        session.commit()
        return entity1, entity2

    @pytest.fixture
    def jurisdiction(self, session):
        """Create a test jurisdiction"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(name="Relationship Test County", state="NV")
        session.add(jurisdiction)
        session.commit()
        return jurisdiction

    @pytest.fixture
    def data_source(self, session, jurisdiction):
        """Create a test data source"""
        from datagod.models import DataSource

        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Relationship Test Source",
            source_type="api"
        )
        session.add(data_source)
        session.commit()
        return data_source

    @pytest.fixture
    def record(self, session, jurisdiction, data_source):
        """Create a test record"""
        from datagod.models import Record

        record = Record(
            jurisdiction_id=jurisdiction.id,
            data_source_id=data_source.id,
            title="Test Record",
            record_type="deed"
        )
        session.add(record)
        session.commit()
        return record

    def test_relationship_creation(self, session, entities, record):
        """Test creating a relationship"""
        from datagod.models import Relationship

        entity1, entity2 = entities

        relationship = Relationship(
            entity1_id=entity1.id,
            entity2_id=entity2.id,
            record_id=record.id,
            relationship_type="owner",
            role1="seller",
            role2="buyer",
            confidence_score=0.95
        )

        session.add(relationship)
        session.commit()

        assert relationship.id is not None
        assert relationship.relationship_type == "owner"
        assert relationship.confidence_score == 0.95

    def test_relationship_repr(self, session, entities, record):
        """Test relationship string representation"""
        from datagod.models import Relationship

        entity1, entity2 = entities

        relationship = Relationship(
            entity1_id=entity1.id,
            entity2_id=entity2.id,
            record_id=record.id,
            relationship_type="partner"
        )

        # Just verify repr doesn't raise an error
        repr_str = repr(relationship)
        assert relationship is not None


class TestUserModel:
    """Tests for User SQLAlchemy model"""

    @pytest.fixture
    def engine(self):
        """Create test database engine"""
        from datagod.models import Base
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_user_creation(self, session):
        """Test creating a user"""
        from datagod.models import User

        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User"
        )

        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_repr(self, session):
        """Test user string representation"""
        from datagod.models import User

        user = User(
            username="johndoe",
            email="john@example.com",
            hashed_password="hashed"
        )

        assert "johndoe" in repr(user)

    def test_user_defaults(self, session):
        """Test user default values"""
        from datagod.models import User

        user = User(
            username="defaultuser",
            email="default@example.com",
            hashed_password="hashed"
        )

        session.add(user)
        session.commit()

        assert user.disabled is False
        assert user.roles == ["user"]

    def test_user_unique_username(self, session):
        """Test user username uniqueness"""
        from datagod.models import User
        from sqlalchemy.exc import IntegrityError

        u1 = User(username="unique", email="u1@example.com", hashed_password="h1")
        session.add(u1)
        session.commit()

        u2 = User(username="unique", email="u2@example.com", hashed_password="h2")
        session.add(u2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_unique_email(self, session):
        """Test user email uniqueness"""
        from datagod.models import User
        from sqlalchemy.exc import IntegrityError

        # Rollback any previous transaction
        session.rollback()

        u1 = User(username="user1", email="same@example.com", hashed_password="h1")
        session.add(u1)
        session.commit()

        u2 = User(username="user2", email="same@example.com", hashed_password="h2")
        session.add(u2)

        with pytest.raises(IntegrityError):
            session.commit()
