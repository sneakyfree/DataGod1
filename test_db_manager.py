"""
Tests for DataGod Database Manager

This module contains tests for the DatabaseManager class and its operations.
"""

import pytest
import os
import tempfile
from datetime import datetime
from typing import Generator

# Use a test database
TEST_DB_PATH = tempfile.mktemp(suffix='.db')
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'

from db_manager import DatabaseManager, get_db_manager


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""

    @pytest.fixture(autouse=True)
    def setup(self) -> Generator:
        """Set up test database before each test."""
        self.db = DatabaseManager(f'sqlite:///{TEST_DB_PATH}')
        self.db.init_database()
        yield
        # Cleanup after each test
        self.db.drop_all_tables()

    # ==================== JURISDICTION TESTS ====================

    def test_create_jurisdiction(self):
        """Test creating a jurisdiction."""
        jid = self.db.create_jurisdiction(
            name="Test County",
            state="TX",
            county="Test",
            jurisdiction_type="county",
            api_available=True,
            description="Test jurisdiction"
        )

        assert jid is not None
        assert jid > 0

    def test_create_duplicate_jurisdiction(self):
        """Test that creating a duplicate jurisdiction returns None."""
        self.db.create_jurisdiction(name="Unique County", state="TX")
        duplicate_id = self.db.create_jurisdiction(name="Unique County", state="CA")

        assert duplicate_id is None

    def test_get_jurisdiction(self):
        """Test getting a jurisdiction by ID."""
        jid = self.db.create_jurisdiction(
            name="Get Test County",
            state="FL",
            population=100000
        )

        jurisdiction = self.db.get_jurisdiction(jid)

        assert jurisdiction is not None
        assert jurisdiction['name'] == "Get Test County"
        assert jurisdiction['state'] == "FL"
        assert jurisdiction['population'] == 100000

    def test_get_jurisdiction_by_name(self):
        """Test getting a jurisdiction by name."""
        self.db.create_jurisdiction(name="Named County", state="CA")

        jurisdiction = self.db.get_jurisdiction_by_name("Named County")

        assert jurisdiction is not None
        assert jurisdiction['state'] == "CA"

    def test_list_jurisdictions(self):
        """Test listing jurisdictions with filters."""
        self.db.create_jurisdiction(name="Florida County 1", state="FL")
        self.db.create_jurisdiction(name="Florida County 2", state="FL")
        self.db.create_jurisdiction(name="California County", state="CA")

        # List all
        all_jurisdictions = self.db.list_jurisdictions()
        assert len(all_jurisdictions) == 3

        # Filter by state
        fl_jurisdictions = self.db.list_jurisdictions(state="FL")
        assert len(fl_jurisdictions) == 2

    def test_update_jurisdiction(self):
        """Test updating a jurisdiction."""
        jid = self.db.create_jurisdiction(name="Update County", state="TX")

        result = self.db.update_jurisdiction(jid, state="CA", population=50000)

        assert result is True

        updated = self.db.get_jurisdiction(jid)
        assert updated['state'] == "CA"
        assert updated['population'] == 50000

    def test_delete_jurisdiction(self):
        """Test deleting a jurisdiction."""
        jid = self.db.create_jurisdiction(name="Delete County", state="TX")

        result = self.db.delete_jurisdiction(jid)

        assert result is True
        assert self.db.get_jurisdiction(jid) is None

    def test_count_jurisdictions(self):
        """Test counting jurisdictions."""
        self.db.create_jurisdiction(name="Count County 1", state="FL")
        self.db.create_jurisdiction(name="Count County 2", state="FL")
        self.db.create_jurisdiction(name="Count County 3", state="CA")

        total = self.db.count_jurisdictions()
        fl_count = self.db.count_jurisdictions(state="FL")

        assert total == 3
        assert fl_count == 2

    # ==================== DATA SOURCE TESTS ====================

    def test_create_data_source(self):
        """Test creating a data source."""
        jid = self.db.create_jurisdiction(name="Source Test County", state="TX")

        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api",
            status="active"
        )

        assert ds_id is not None
        assert ds_id > 0

    def test_get_data_source(self):
        """Test getting a data source."""
        jid = self.db.create_jurisdiction(name="DS Get County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Get Test API",
            source_type="api"
        )

        data_source = self.db.get_data_source(ds_id)

        assert data_source is not None
        assert data_source['source_name'] == "Get Test API"
        assert data_source['source_type'] == "api"

    def test_list_data_sources(self):
        """Test listing data sources."""
        jid = self.db.create_jurisdiction(name="DS List County", state="TX")
        self.db.create_data_source(jurisdiction_id=jid, source_name="API 1", source_type="api")
        self.db.create_data_source(jurisdiction_id=jid, source_name="Scraper 1", source_type="scraper")

        all_sources = self.db.list_data_sources(jurisdiction_id=jid)
        api_sources = self.db.list_data_sources(jurisdiction_id=jid, source_type="api")

        assert len(all_sources) == 2
        assert len(api_sources) == 1

    def test_record_scrape(self):
        """Test recording a scrape attempt."""
        jid = self.db.create_jurisdiction(name="Scrape Test County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Scrape Test",
            source_type="scraper"
        )

        # Record successful scrape
        result = self.db.record_scrape(ds_id, success=True)
        assert result is True

        ds = self.db.get_data_source(ds_id)
        assert ds['success_count'] == 1
        assert ds['last_scraped'] is not None

    # ==================== RECORD TESTS ====================

    def test_create_record(self):
        """Test creating a record."""
        jid = self.db.create_jurisdiction(name="Record Test County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Record Test API",
            source_type="api"
        )

        record_id = self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Test Mortgage Record",
            amount=250000.00,
            grantor="John Doe",
            grantee="Bank of Test"
        )

        assert record_id is not None
        assert record_id > 0

    def test_get_record(self):
        """Test getting a record."""
        jid = self.db.create_jurisdiction(name="Get Record County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Get Record API",
            source_type="api"
        )
        record_id = self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="deed",
            title="Test Deed",
            amount=350000.00
        )

        record = self.db.get_record(record_id)

        assert record is not None
        assert record['record_type'] == "deed"
        assert record['title'] == "Test Deed"
        assert record['amount'] == 350000.00

    def test_search_records(self):
        """Test searching records."""
        jid = self.db.create_jurisdiction(name="Search County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Search API",
            source_type="api"
        )

        # Create test records
        self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Mortgage on Main Street",
            grantor="Alice Smith"
        )
        self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="deed",
            title="Deed for Oak Avenue",
            grantor="Bob Jones"
        )

        # Search by query
        mortgage_results = self.db.search_records(query="mortgage")
        assert len(mortgage_results) >= 1

        # Search by type
        deed_results = self.db.search_records(record_type="deed")
        assert len(deed_results) >= 1

        # Search by grantor
        alice_results = self.db.search_records(grantor="Alice")
        assert len(alice_results) >= 1

    def test_bulk_create_records(self):
        """Test bulk creating records."""
        jid = self.db.create_jurisdiction(name="Bulk County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Bulk API",
            source_type="api"
        )

        records = [
            {
                "jurisdiction_id": jid,
                "data_source_id": ds_id,
                "record_type": "mortgage",
                "title": f"Bulk Record {i}"
            }
            for i in range(10)
        ]

        count = self.db.bulk_create_records(records)

        assert count == 10

    def test_count_records(self):
        """Test counting records."""
        jid = self.db.create_jurisdiction(name="Count Records County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Count API",
            source_type="api"
        )

        for i in range(5):
            self.db.create_record(
                jurisdiction_id=jid,
                data_source_id=ds_id,
                record_type="mortgage" if i % 2 == 0 else "deed",
                title=f"Count Record {i}"
            )

        total = self.db.count_records()
        mortgage_count = self.db.count_records(record_type="mortgage")

        assert total == 5
        assert mortgage_count == 3  # 0, 2, 4

    # ==================== ENTITY TESTS ====================

    def test_create_entity(self):
        """Test creating an entity."""
        entity_id = self.db.create_entity(
            entity_name="Test Person",
            entity_type="person",
            city="Miami",
            state="FL"
        )

        assert entity_id is not None
        assert entity_id > 0

    def test_get_entity(self):
        """Test getting an entity."""
        eid = self.db.create_entity(
            entity_name="Get Test Company",
            entity_type="company",
            city="Houston",
            state="TX"
        )

        entity = self.db.get_entity(eid)

        assert entity is not None
        assert entity['entity_name'] == "Get Test Company"
        assert entity['entity_type'] == "company"

    def test_search_entities(self):
        """Test searching entities."""
        self.db.create_entity(entity_name="John Smith", entity_type="person", state="FL")
        self.db.create_entity(entity_name="Jane Doe", entity_type="person", state="CA")
        self.db.create_entity(entity_name="ABC Company", entity_type="company", state="TX")

        # Search by name
        john_results = self.db.search_entities(query="John")
        assert len(john_results) == 1

        # Search by type
        person_results = self.db.search_entities(entity_type="person")
        assert len(person_results) == 2

    # ==================== RELATIONSHIP TESTS ====================

    def test_create_relationship(self):
        """Test creating a relationship."""
        # Create entities
        entity1_id = self.db.create_entity(entity_name="Borrower", entity_type="person")
        entity2_id = self.db.create_entity(entity_name="Lender Bank", entity_type="company")

        # Create a record
        jid = self.db.create_jurisdiction(name="Rel County", state="TX")
        ds_id = self.db.create_data_source(jurisdiction_id=jid, source_name="Rel API", source_type="api")
        record_id = self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Test Mortgage"
        )

        # Create relationship
        rel_id = self.db.create_relationship(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            record_id=record_id,
            relationship_type="borrower-lender",
            role1="borrower",
            role2="lender"
        )

        assert rel_id is not None
        assert rel_id > 0

    def test_get_entity_relationships(self):
        """Test getting relationships for an entity."""
        # Setup
        entity1_id = self.db.create_entity(entity_name="Person A", entity_type="person")
        entity2_id = self.db.create_entity(entity_name="Company B", entity_type="company")
        entity3_id = self.db.create_entity(entity_name="Company C", entity_type="company")

        jid = self.db.create_jurisdiction(name="Rel Test County", state="TX")
        ds_id = self.db.create_data_source(jurisdiction_id=jid, source_name="Rel Test API", source_type="api")
        record_id = self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Test"
        )

        # Create relationships
        self.db.create_relationship(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            record_id=record_id,
            relationship_type="employer"
        )
        self.db.create_relationship(
            entity1_id=entity1_id,
            entity2_id=entity3_id,
            record_id=record_id,
            relationship_type="investor"
        )

        relationships = self.db.get_entity_relationships(entity1_id)

        assert len(relationships) == 2

    # ==================== DASHBOARD TESTS ====================

    def test_get_dashboard_stats(self):
        """Test getting dashboard statistics."""
        # Create some test data
        jid = self.db.create_jurisdiction(name="Stats County", state="TX")
        ds_id = self.db.create_data_source(
            jurisdiction_id=jid,
            source_name="Stats API",
            source_type="api",
            status="active"
        )
        self.db.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Stats Record"
        )
        self.db.create_entity(entity_name="Stats Entity", entity_type="person")

        stats = self.db.get_dashboard_stats()

        assert stats['totalRecords'] >= 1
        assert stats['jurisdictions'] >= 1
        assert stats['dataSources'] >= 1
        assert stats['activeScrapers'] >= 1
        assert stats['totalEntities'] >= 1

    # ==================== DATABASE MANAGEMENT TESTS ====================

    def test_init_database(self):
        """Test database initialization."""
        result = self.db.init_database()
        assert result is True

    def test_reset_database(self):
        """Test database reset."""
        # Create some data
        self.db.create_jurisdiction(name="Reset Test", state="TX")

        # Reset
        result = self.db.reset_database()
        assert result is True

        # Verify data is gone
        jurisdictions = self.db.list_jurisdictions()
        assert len(jurisdictions) == 0


class TestConvenienceFunctions:
    """Test suite for module-level convenience functions."""

    def test_get_db_manager(self):
        """Test getting the global database manager."""
        db = get_db_manager()
        assert db is not None
        assert isinstance(db, DatabaseManager)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
