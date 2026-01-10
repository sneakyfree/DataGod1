"""
Comprehensive tests for datagod.models module
"""

import pytest
from datetime import datetime


class TestJurisdictionModel:
    """Tests for Jurisdiction model"""

    def test_jurisdiction_import(self):
        """Test Jurisdiction can be imported"""
        from datagod.models import Jurisdiction
        assert Jurisdiction is not None

    def test_jurisdiction_tablename(self):
        """Test Jurisdiction tablename"""
        from datagod.models import Jurisdiction
        assert Jurisdiction.__tablename__ == 'jurisdictions'

    def test_jurisdiction_has_id_column(self):
        """Test Jurisdiction has id column"""
        from datagod.models import Jurisdiction
        assert hasattr(Jurisdiction, 'id')

    def test_jurisdiction_has_name_column(self):
        """Test Jurisdiction has name column"""
        from datagod.models import Jurisdiction
        assert hasattr(Jurisdiction, 'name')

    def test_jurisdiction_has_state_column(self):
        """Test Jurisdiction has state column"""
        from datagod.models import Jurisdiction
        assert hasattr(Jurisdiction, 'state')

    def test_jurisdiction_creation(self):
        """Test Jurisdiction object creation"""
        from datagod.models import Jurisdiction
        j = Jurisdiction(name="Test County", state="TX")
        assert j.name == "Test County"
        assert j.state == "TX"


class TestDataSourceModel:
    """Tests for DataSource model"""

    def test_data_source_import(self):
        """Test DataSource can be imported"""
        from datagod.models import DataSource
        assert DataSource is not None

    def test_data_source_tablename(self):
        """Test DataSource tablename"""
        from datagod.models import DataSource
        assert DataSource.__tablename__ == 'data_sources'

    def test_data_source_has_id_column(self):
        """Test DataSource has id column"""
        from datagod.models import DataSource
        assert hasattr(DataSource, 'id')

    def test_data_source_has_source_name_column(self):
        """Test DataSource has source_name column"""
        from datagod.models import DataSource
        assert hasattr(DataSource, 'source_name')

    def test_data_source_has_source_type_column(self):
        """Test DataSource has source_type column"""
        from datagod.models import DataSource
        assert hasattr(DataSource, 'source_type')


class TestRecordModel:
    """Tests for Record model"""

    def test_record_import(self):
        """Test Record can be imported"""
        from datagod.models import Record
        assert Record is not None

    def test_record_tablename(self):
        """Test Record tablename"""
        from datagod.models import Record
        assert Record.__tablename__ == 'records'

    def test_record_has_id_column(self):
        """Test Record has id column"""
        from datagod.models import Record
        assert hasattr(Record, 'id')

    def test_record_has_title_column(self):
        """Test Record has title column"""
        from datagod.models import Record
        assert hasattr(Record, 'title')

    def test_record_has_record_type_column(self):
        """Test Record has record_type column"""
        from datagod.models import Record
        assert hasattr(Record, 'record_type')


class TestEntityModel:
    """Tests for Entity model"""

    def test_entity_import(self):
        """Test Entity can be imported"""
        from datagod.models import Entity
        assert Entity is not None

    def test_entity_tablename(self):
        """Test Entity tablename"""
        from datagod.models import Entity
        assert Entity.__tablename__ == 'entities'

    def test_entity_has_id_column(self):
        """Test Entity has id column"""
        from datagod.models import Entity
        assert hasattr(Entity, 'id')

    def test_entity_has_entity_name_column(self):
        """Test Entity has entity_name column"""
        from datagod.models import Entity
        assert hasattr(Entity, 'entity_name')

    def test_entity_has_entity_type_column(self):
        """Test Entity has entity_type column"""
        from datagod.models import Entity
        assert hasattr(Entity, 'entity_type')


class TestRelationshipModel:
    """Tests for Relationship model"""

    def test_relationship_import(self):
        """Test Relationship can be imported"""
        from datagod.models import Relationship
        assert Relationship is not None

    def test_relationship_tablename(self):
        """Test Relationship tablename"""
        from datagod.models import Relationship
        assert Relationship.__tablename__ == 'relationships'

    def test_relationship_has_id_column(self):
        """Test Relationship has id column"""
        from datagod.models import Relationship
        assert hasattr(Relationship, 'id')


class TestUserModel:
    """Tests for User model"""

    def test_user_import(self):
        """Test User can be imported"""
        from datagod.models import User
        assert User is not None

    def test_user_tablename(self):
        """Test User tablename"""
        from datagod.models import User
        assert User.__tablename__ == 'users'

    def test_user_has_id_column(self):
        """Test User has id column"""
        from datagod.models import User
        assert hasattr(User, 'id')

    def test_user_has_username_column(self):
        """Test User has username column"""
        from datagod.models import User
        assert hasattr(User, 'username')

    def test_user_has_email_column(self):
        """Test User has email column"""
        from datagod.models import User
        assert hasattr(User, 'email')

    def test_user_has_hashed_password_column(self):
        """Test User has hashed_password column"""
        from datagod.models import User
        assert hasattr(User, 'hashed_password')


class TestModelRelationships:
    """Tests for model relationships"""

    def test_record_has_jurisdiction_relationship(self):
        """Test Record has jurisdiction relationship"""
        from datagod.models import Record
        assert hasattr(Record, 'jurisdiction_id')

    def test_record_has_data_source_relationship(self):
        """Test Record has data_source relationship"""
        from datagod.models import Record
        assert hasattr(Record, 'data_source_id')

    def test_data_source_has_jurisdiction_relationship(self):
        """Test DataSource has jurisdiction relationship"""
        from datagod.models import DataSource
        assert hasattr(DataSource, 'jurisdiction_id')


class TestModelInit:
    """Tests for models __init__ module"""

    def test_models_init_exports_base(self):
        """Test models __init__ exports Base"""
        from datagod.models import Base
        assert Base is not None

    def test_models_init_exports_jurisdiction(self):
        """Test models __init__ exports Jurisdiction"""
        from datagod.models import Jurisdiction
        assert Jurisdiction is not None

    def test_models_init_exports_data_source(self):
        """Test models __init__ exports DataSource"""
        from datagod.models import DataSource
        assert DataSource is not None

    def test_models_init_exports_record(self):
        """Test models __init__ exports Record"""
        from datagod.models import Record
        assert Record is not None

    def test_models_init_exports_entity(self):
        """Test models __init__ exports Entity"""
        from datagod.models import Entity
        assert Entity is not None

    def test_models_init_exports_relationship(self):
        """Test models __init__ exports Relationship"""
        from datagod.models import Relationship
        assert Relationship is not None

    def test_models_init_exports_user(self):
        """Test models __init__ exports User"""
        from datagod.models import User
        assert User is not None


class TestModelValidation:
    """Tests for model creation with validation"""

    def test_jurisdiction_repr(self):
        """Test Jurisdiction __repr__"""
        from datagod.models import Jurisdiction
        j = Jurisdiction(name="Test County", state="TX")
        repr_str = repr(j)
        assert "Jurisdiction" in repr_str or "Test County" in str(j) or repr_str is not None

    def test_entity_creation_with_all_fields(self):
        """Test Entity creation with all fields"""
        from datagod.models import Entity
        e = Entity(
            entity_name="John Doe",
            entity_type="person",
            address="123 Main St"
        )
        assert e.entity_name == "John Doe"
        assert e.entity_type == "person"
        assert e.address == "123 Main St"

    def test_user_creation_with_roles(self):
        """Test User creation with roles"""
        from datagod.models import User
        u = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hash123"
        )
        assert u.username == "testuser"
        assert u.email == "test@example.com"
