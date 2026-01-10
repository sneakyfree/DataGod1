"""
Tests for DataGod models
"""

import pytest
from datetime import datetime


class TestJurisdictionModel:
    """Tests for Jurisdiction model"""

    def test_jurisdiction_creation(self, db_session, sample_jurisdiction_data):
        """Test creating a jurisdiction"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        assert jurisdiction.id is not None
        assert jurisdiction.name == "Test County"
        assert jurisdiction.state == "TX"
        assert jurisdiction.type == "county"
        assert jurisdiction.api_available == True

    def test_jurisdiction_repr(self, db_session, sample_jurisdiction_data):
        """Test jurisdiction string representation"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        repr_str = repr(jurisdiction)
        assert "Test County" in repr_str
        assert "TX" in repr_str


class TestRecordModel:
    """Tests for Record model"""

    def test_record_creation(self, db_session, sample_jurisdiction_data, sample_record_data):
        """Test creating a record"""
        from datagod.models import Jurisdiction, Record, DataSource

        # Create jurisdiction first
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test API",
            source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create record
        sample_record_data["jurisdiction_id"] = jurisdiction.id
        sample_record_data["data_source_id"] = data_source.id
        record = Record(**sample_record_data)
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.record_type == "mortgage"
        assert record.grantor == "John Doe"
        assert record.amount == 250000.00

    def test_record_timestamps(self, db_session, sample_jurisdiction_data, sample_record_data):
        """Test record timestamp fields"""
        from datagod.models import Jurisdiction, Record, DataSource

        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test API",
            source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        sample_record_data["jurisdiction_id"] = jurisdiction.id
        sample_record_data["data_source_id"] = data_source.id
        record = Record(**sample_record_data)
        db_session.add(record)
        db_session.commit()

        assert record.created_at is not None
        assert record.updated_at is not None


class TestEntityModel:
    """Tests for Entity model"""

    def test_entity_creation(self, db_session, sample_entity_data):
        """Test creating an entity"""
        from datagod.models import Entity

        entity = Entity(**sample_entity_data)
        db_session.add(entity)
        db_session.commit()

        assert entity.id is not None
        assert entity.entity_name == "Test Corporation LLC"
        assert entity.entity_type == "company"

    def test_entity_repr(self, db_session, sample_entity_data):
        """Test entity string representation"""
        from datagod.models import Entity

        entity = Entity(**sample_entity_data)
        db_session.add(entity)
        db_session.commit()

        repr_str = repr(entity)
        assert "Test Corporation LLC" in repr_str
        assert "company" in repr_str


class TestRelationshipModel:
    """Tests for Relationship model"""

    def test_relationship_creation(self, db_session, sample_jurisdiction_data, sample_record_data, sample_entity_data):
        """Test creating a relationship"""
        from datagod.models import Jurisdiction, Record, Entity, Relationship, DataSource

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test API",
            source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create record
        sample_record_data["jurisdiction_id"] = jurisdiction.id
        sample_record_data["data_source_id"] = data_source.id
        record = Record(**sample_record_data)
        db_session.add(record)
        db_session.commit()

        # Create entities
        entity1 = Entity(**sample_entity_data)
        entity2_data = sample_entity_data.copy()
        entity2_data["entity_name"] = "Another Company"
        entity2 = Entity(**entity2_data)
        db_session.add(entity1)
        db_session.add(entity2)
        db_session.commit()

        # Create relationship
        relationship = Relationship(
            entity1_id=entity1.id,
            entity2_id=entity2.id,
            record_id=record.id,
            relationship_type="borrower",
            role1="borrower",
            role2="lender",
            confidence_score=0.95,
            status="active"
        )
        db_session.add(relationship)
        db_session.commit()

        assert relationship.id is not None
        assert relationship.relationship_type == "borrower"
        assert relationship.confidence_score == 0.95


class TestDataSourceModel:
    """Tests for DataSource model"""

    def test_data_source_creation(self, db_session, sample_jurisdiction_data):
        """Test creating a data source"""
        from datagod.models import Jurisdiction, DataSource

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id,
            source_name="Test API",
            source_type="api",
            api_endpoint="https://api.test.gov",
            status="active"
        )
        db_session.add(data_source)
        db_session.commit()

        assert data_source.id is not None
        assert data_source.source_name == "Test API"
        assert data_source.source_type == "api"
