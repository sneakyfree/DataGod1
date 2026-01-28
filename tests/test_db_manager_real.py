
import pytest
from datetime import datetime, date
from db_manager import DatabaseManager
from datagod.models import Base

# Fixture for DatabaseManager with in-memory SQLite
@pytest.fixture
def db_manager():
    # Use SQLite in-memory database
    db_url = "sqlite:///:memory:"
    manager = DatabaseManager(database_url=db_url)
    
    # Create tables
    Base.metadata.create_all(manager.engine)
    
    yield manager
    
    # Drop tables (cleanup)
    Base.metadata.drop_all(manager.engine)

class TestDatabaseManagerReal:
    """Real functional tests for DatabaseManager using SQLite"""

    def test_jurisdiction_crud(self, db_manager):
        # Create
        jid = db_manager.create_jurisdiction(
            name="Test County",
            state="TX",
            jurisdiction_type="county",
            api_available=True
        )
        assert jid is not None
        
        # Get
        j = db_manager.get_jurisdiction(jid)
        assert j is not None
        assert j['name'] == "Test County"
        assert j['state'] == "TX"
        
        # Get by name
        j_name = db_manager.get_jurisdiction_by_name("Test County")
        assert j_name['id'] == jid
        
        # Update
        success = db_manager.update_jurisdiction(jid, population=5000)
        assert success is True
        j_updated = db_manager.get_jurisdiction(jid)
        assert j_updated['population'] == 5000
        
        # List
        j_list = db_manager.list_jurisdictions(state="TX")
        assert len(j_list) == 1
        assert j_list[0]['id'] == jid
        
        # Count
        count = db_manager.count_jurisdictions(state="TX")
        assert count == 1
        
        # Delete
        success = db_manager.delete_jurisdiction(jid)
        assert success is True
        
        j_deleted = db_manager.get_jurisdiction(jid)
        assert j_deleted is None

    def test_data_source_crud(self, db_manager):
        # Setup jurisdiction
        jid = db_manager.create_jurisdiction(name="County A", state="CA")
        
        # Create Data Source
        ds_id = db_manager.create_data_source(
            jurisdiction_id=jid,
            source_name="API Source",
            source_type="api",
            status="active"
        )
        assert ds_id is not None
        
        # Get
        ds = db_manager.get_data_source(ds_id)
        assert ds['source_name'] == "API Source"
        
        # List
        ds_list = db_manager.list_data_sources(jurisdiction_id=jid)
        assert len(ds_list) == 1
        
        # Update Status
        db_manager.update_data_source_status(ds_id, status="error", error_count=1)
        ds_updated = db_manager.get_data_source(ds_id)
        assert ds_updated['status'] == "error"
        assert ds_updated['error_count'] == 1
        
        # Record Scrape
        db_manager.record_scrape(ds_id, success=True)
        ds_scraped = db_manager.get_data_source(ds_id)
        assert ds_scraped['status'] == "active"
        assert ds_scraped['last_scraped'] is not None

    def test_record_crud(self, db_manager):
        jid = db_manager.create_jurisdiction(name="County B", state="FL")
        ds_id = db_manager.create_data_source(jurisdiction_id=jid, source_name="Src", source_type="api")
        
        # Create Record
        rid = db_manager.create_record(
            jurisdiction_id=jid,
            data_source_id=ds_id,
            record_type="mortgage",
            title="Mortgage 1",
            amount=100000.0,
            date=datetime(2024, 1, 1),
            grantor="John",
            grantee="Bank"
        )
        assert rid is not None
        
        # Get
        r = db_manager.get_record(rid)
        assert r['title'] == "Mortgage 1"
        assert r['amount'] == 100000.0
        
        # Search
        results = db_manager.search_records(query="Mortgage", amount_min=50000)
        assert len(results) == 1
        
        # Count
        count = db_manager.count_records(record_type="mortgage")
        assert count == 1
        
        # Stats
        stats = db_manager.get_record_stats()
        assert stats['total_records'] == 1
        assert stats['total_amount'] == 100000.0

    def test_entity_crud(self, db_manager):
        eid = db_manager.create_entity(
            entity_name="Alice",
            entity_type="person",
            city="Miami"
        )
        assert eid is not None
        
        e = db_manager.get_entity(eid)
        assert e['entity_name'] == "Alice"
        
        results = db_manager.search_entities(query="Alice")
        assert len(results) == 1

    def test_bulk_create(self, db_manager):
        jid = db_manager.create_jurisdiction(name="County C", state="NY")
        ds_id = db_manager.create_data_source(jurisdiction_id=jid, source_name="Bulk Src", source_type="api")
        
        records = [
            {
                "jurisdiction_id": jid,
                "data_source_id": ds_id,
                "title": f"Record {i}",
                "record_type": "deed",
                "amount": 1000.0 * i
            }
            for i in range(10)
        ]
        
        count = db_manager.bulk_create_records(records)
        assert count == 10
        assert db_manager.count_records() == 10
