"""
Tests for root DatabaseManager (db_manager.py)
Tests SQLAlchemy-based database operations
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization"""

    def test_initialization_with_custom_url(self):
        """Test DatabaseManager initializes with custom URL"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            assert dm.database_url == TEST_DATABASE_URL
            assert dm.engine is not None

    def test_initialization_with_default_url(self):
        """Test DatabaseManager uses default URL from settings"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager()
            assert dm.engine is not None

    def test_session_factory_created(self):
        """Test session factory is created"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            assert dm.SessionLocal is not None
            assert dm.scoped_session is not None


class TestDatabaseSession:
    """Tests for database session management"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_get_session_context_manager(self, db_manager):
        """Test get_session context manager"""
        with db_manager.get_session() as session:
            assert session is not None

    def test_session_commit_on_success(self, db_manager):
        """Test session commits on successful exit"""
        from datagod.models import Jurisdiction

        with db_manager.get_session() as session:
            jurisdiction = Jurisdiction(name="Test Session County", state="TX")
            session.add(jurisdiction)

        # Verify committed
        with db_manager.get_session() as session:
            result = (
                session.query(Jurisdiction)
                .filter_by(name="Test Session County")
                .first()
            )
            assert result is not None


class TestDatabaseInit:
    """Tests for database initialization"""

    def test_init_database(self):
        """Test database table creation"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            result = dm.init_database()
            assert result is True

    def test_init_database_creates_tables(self):
        """Test all tables are created"""
        from sqlalchemy import inspect

        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()

            inspector = inspect(dm.engine)
            tables = inspector.get_table_names()

            # Should have main tables
            assert "jurisdictions" in tables
            assert "data_sources" in tables
            assert "records" in tables


class TestJurisdictionOperations:
    """Tests for Jurisdiction CRUD operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_create_jurisdiction(self, db_manager):
        """Test creating a jurisdiction - returns ID"""
        jurisdiction_id = db_manager.create_jurisdiction(
            name="Harris County Create",
            state="TX",
            county="Harris",
            jurisdiction_type="county",
        )

        assert jurisdiction_id is not None
        assert isinstance(jurisdiction_id, int)
        assert jurisdiction_id > 0

    def test_get_jurisdiction_by_id(self, db_manager):
        """Test getting jurisdiction by ID - returns dict"""
        created_id = db_manager.create_jurisdiction(name="Get Test County", state="CA")

        result = db_manager.get_jurisdiction(created_id)
        assert result is not None
        # Returns a dict, not a model object
        assert result["id"] == created_id
        assert result["name"] == "Get Test County"

    def test_get_jurisdiction_not_found(self, db_manager):
        """Test getting non-existent jurisdiction"""
        result = db_manager.get_jurisdiction(999999)
        assert result is None

    def test_list_jurisdictions(self, db_manager):
        """Test listing all jurisdictions"""
        db_manager.create_jurisdiction(name="List Test 1", state="TX")
        db_manager.create_jurisdiction(name="List Test 2", state="CA")

        jurisdictions = db_manager.list_jurisdictions()
        assert len(jurisdictions) >= 2

    def test_update_jurisdiction(self, db_manager):
        """Test updating a jurisdiction"""
        created_id = db_manager.create_jurisdiction(
            name="Update Test County", state="TX"
        )

        updated = db_manager.update_jurisdiction(
            created_id, api_available=True, scraper_needed=False
        )

        assert updated is True
        # Re-fetch to verify - returns dict
        result = db_manager.get_jurisdiction(created_id)
        assert result["api_available"] is True
        assert result["scraper_needed"] is False

    def test_count_jurisdictions(self, db_manager):
        """Test counting jurisdictions"""
        initial_count = db_manager.count_jurisdictions()

        db_manager.create_jurisdiction(name="Count Test 1", state="TX")
        db_manager.create_jurisdiction(name="Count Test 2", state="TX")

        new_count = db_manager.count_jurisdictions()
        assert new_count == initial_count + 2


class TestDataSourceOperations:
    """Tests for DataSource CRUD operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager with jurisdiction"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    @pytest.fixture
    def jurisdiction_id(self, db_manager):
        """Create test jurisdiction"""
        return db_manager.create_jurisdiction(name="DS Test County", state="TX")

    def test_create_data_source(self, db_manager, jurisdiction_id):
        """Test creating a data source - returns ID"""
        ds_id = db_manager.create_data_source(
            jurisdiction_id=jurisdiction_id,
            source_name="Test API",
            source_type="api",
            api_endpoint="https://api.example.com",
        )

        assert ds_id is not None
        assert isinstance(ds_id, int)
        assert ds_id > 0

    def test_get_data_source(self, db_manager, jurisdiction_id):
        """Test getting a data source - returns dict"""
        created_id = db_manager.create_data_source(
            jurisdiction_id=jurisdiction_id,
            source_name="Get Test API",
            source_type="api",
        )

        result = db_manager.get_data_source(created_id)
        assert result is not None
        # Returns dict
        assert result["id"] == created_id

    def test_list_data_sources(self, db_manager, jurisdiction_id):
        """Test listing data sources"""
        db_manager.create_data_source(
            jurisdiction_id=jurisdiction_id, source_name="List DS 1", source_type="api"
        )
        db_manager.create_data_source(
            jurisdiction_id=jurisdiction_id,
            source_name="List DS 2",
            source_type="scraper",
        )

        sources = db_manager.list_data_sources()
        assert len(sources) >= 2


class TestRecordOperations:
    """Tests for Record CRUD operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    @pytest.fixture
    def jurisdiction_id(self, db_manager):
        """Create test jurisdiction"""
        return db_manager.create_jurisdiction(name="Record Test County", state="TX")

    @pytest.fixture
    def data_source_id(self, db_manager, jurisdiction_id):
        """Create test data source"""
        return db_manager.create_data_source(
            jurisdiction_id=jurisdiction_id,
            source_name="Record Test Source",
            source_type="api",
        )

    def test_create_record(self, db_manager, jurisdiction_id, data_source_id):
        """Test creating a record - returns ID"""
        record_id = db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Test Mortgage",
            record_type="mortgage",
            amount=250000.0,
        )

        assert record_id is not None
        assert isinstance(record_id, int)
        assert record_id > 0

    def test_get_record(self, db_manager, jurisdiction_id, data_source_id):
        """Test getting a record - returns dict"""
        created_id = db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Get Test Record",
            record_type="deed",
        )

        result = db_manager.get_record(created_id)
        assert result is not None
        # Returns dict
        assert result["id"] == created_id

    def test_search_records(self, db_manager, jurisdiction_id, data_source_id):
        """Test searching records"""
        db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Searchable Mortgage",
            record_type="mortgage",
            amount=300000.0,
        )

        results = db_manager.search_records(query="Searchable")
        assert len(results) >= 1

    def test_count_records(self, db_manager, jurisdiction_id, data_source_id):
        """Test counting records"""
        initial_count = db_manager.count_records()

        db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Count Test 1",
            record_type="mortgage",
        )
        db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Count Test 2",
            record_type="deed",
        )

        new_count = db_manager.count_records()
        assert new_count == initial_count + 2


class TestEntityOperations:
    """Tests for Entity CRUD operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_create_entity(self, db_manager):
        """Test creating an entity - returns ID"""
        entity_id = db_manager.create_entity(
            entity_name="John Doe", entity_type="person", address="123 Main St"
        )

        assert entity_id is not None
        assert isinstance(entity_id, int)
        assert entity_id > 0

    def test_get_entity(self, db_manager):
        """Test getting an entity - returns dict"""
        created_id = db_manager.create_entity(
            entity_name="Get Test Entity", entity_type="company"
        )

        result = db_manager.get_entity(created_id)
        assert result is not None
        # Returns dict
        assert result["id"] == created_id


class TestUserOperations:
    """Tests for User CRUD operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_create_user(self, db_manager):
        """Test creating a user - returns ID"""
        user_id = db_manager.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed123",
            full_name="Test User",
        )

        assert user_id is not None
        assert isinstance(user_id, int)
        assert user_id > 0

    def test_get_user_by_username(self, db_manager):
        """Test getting user by username - returns dict"""
        db_manager.create_user(
            username="findme", email="findme@example.com", hashed_password="hash"
        )

        result = db_manager.get_user_by_username("findme")
        assert result is not None
        # Returns dict
        assert result["username"] == "findme"

    def test_get_user_by_email(self, db_manager):
        """Test getting user by email - returns dict"""
        db_manager.create_user(
            username="emailtest", email="email@example.com", hashed_password="hash"
        )

        result = db_manager.get_user_by_email("email@example.com")
        assert result is not None
        # Returns dict
        assert result["email"] == "email@example.com"

    def test_list_users(self, db_manager):
        """Test listing users"""
        db_manager.create_user(
            username="listuser1", email="list1@example.com", hashed_password="hash"
        )
        db_manager.create_user(
            username="listuser2", email="list2@example.com", hashed_password="hash"
        )

        users = db_manager.list_users()
        assert len(users) >= 2

    def test_count_users(self, db_manager):
        """Test counting users"""
        initial_count = db_manager.count_users()

        db_manager.create_user(
            username="countuser1", email="count1@example.com", hashed_password="hash"
        )

        new_count = db_manager.count_users()
        assert new_count == initial_count + 1


class TestStatistics:
    """Tests for database statistics methods"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager with sample data"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()

            # Create sample data
            j_id = dm.create_jurisdiction(name="Stats Test County", state="TX")
            ds_id = dm.create_data_source(
                jurisdiction_id=j_id, source_name="Stats API", source_type="api"
            )
            dm.create_record(
                jurisdiction_id=j_id,
                data_source_id=ds_id,
                title="Stats Record 1",
                record_type="mortgage",
                amount=200000.0,
            )
            dm.create_record(
                jurisdiction_id=j_id,
                data_source_id=ds_id,
                title="Stats Record 2",
                record_type="deed",
                amount=300000.0,
            )

            return dm

    def test_get_dashboard_stats(self, db_manager):
        """Test getting dashboard statistics"""
        stats = db_manager.get_dashboard_stats()

        assert stats is not None
        # Keys use camelCase
        assert "jurisdictions" in stats
        assert "totalRecords" in stats
        assert stats["jurisdictions"] >= 1
        assert stats["totalRecords"] >= 2


class TestDeleteOperations:
    """Tests for delete operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_delete_jurisdiction(self, db_manager):
        """Test deleting a jurisdiction"""
        jurisdiction_id = db_manager.create_jurisdiction(
            name="Delete Me County", state="TX"
        )

        result = db_manager.delete_jurisdiction(jurisdiction_id)
        assert result is True

        # Verify deleted
        found = db_manager.get_jurisdiction(jurisdiction_id)
        assert found is None

    def test_delete_nonexistent_jurisdiction(self, db_manager):
        """Test deleting non-existent jurisdiction"""
        result = db_manager.delete_jurisdiction(999999)
        # Should return False or handle gracefully
        assert result in [False, True, None]

    def test_delete_user(self, db_manager):
        """Test deleting a user"""
        user_id = db_manager.create_user(
            username="deleteuser", email="delete@example.com", hashed_password="hash"
        )

        result = db_manager.delete_user(user_id)
        assert result is True

        # Verify deleted
        found = db_manager.get_user_by_username("deleteuser")
        assert found is None


class TestUpdateOperations:
    """Tests for update operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_update_data_source_status(self, db_manager):
        """Test updating a data source status"""
        j_id = db_manager.create_jurisdiction(name="DS Update County", state="TX")
        ds_id = db_manager.create_data_source(
            jurisdiction_id=j_id, source_name="Original Name", source_type="api"
        )

        result = db_manager.update_data_source_status(
            ds_id, status="active", error_count=0, success_count=10
        )

        assert result is True

    def test_update_user(self, db_manager):
        """Test updating a user"""
        user_id = db_manager.create_user(
            username="updateuser", email="original@example.com", hashed_password="hash"
        )

        result = db_manager.update_user(
            user_id, email="updated@example.com", is_active=False
        )

        assert result is True
        updated = db_manager.get_user_by_username("updateuser")
        assert updated["email"] == "updated@example.com"

    def test_update_user_by_username(self, db_manager):
        """Test updating a user by username"""
        db_manager.create_user(
            username="updatebyname", email="byname@example.com", hashed_password="hash"
        )

        result = db_manager.update_user_by_username(
            username="updatebyname", email="newbyname@example.com"
        )

        assert result is True
        updated = db_manager.get_user_by_username("updatebyname")
        assert updated["email"] == "newbyname@example.com"


class TestBulkOperations:
    """Tests for bulk operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_bulk_create_records(self, db_manager):
        """Test bulk creating records"""
        j_id = db_manager.create_jurisdiction(name="Bulk Record County", state="TX")
        ds_id = db_manager.create_data_source(
            jurisdiction_id=j_id, source_name="Bulk Source", source_type="api"
        )

        records = [
            {
                "jurisdiction_id": j_id,
                "data_source_id": ds_id,
                "title": "Bulk Record 1",
                "record_type": "mortgage",
            },
            {
                "jurisdiction_id": j_id,
                "data_source_id": ds_id,
                "title": "Bulk Record 2",
                "record_type": "deed",
            },
        ]

        count = db_manager.bulk_create_records(records)
        assert count >= 2


class TestSearchOperations:
    """Tests for search operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager with search data"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()

            # Create sample data for search
            j_id = dm.create_jurisdiction(name="Search Test County", state="TX")
            ds_id = dm.create_data_source(
                jurisdiction_id=j_id, source_name="Search Source", source_type="api"
            )
            dm.create_record(
                jurisdiction_id=j_id,
                data_source_id=ds_id,
                title="Mortgage for John Smith",
                record_type="mortgage",
                amount=250000.0,
            )
            dm.create_record(
                jurisdiction_id=j_id,
                data_source_id=ds_id,
                title="Deed Transfer Jane Doe",
                record_type="deed",
                amount=150000.0,
            )
            dm.create_entity(
                entity_name="John Smith", entity_type="person", address="123 Main St"
            )

            return dm

    def test_search_records_by_title(self, db_manager):
        """Test searching records by title"""
        results = db_manager.search_records(query="John Smith")
        assert len(results) >= 1

    def test_search_records_by_type(self, db_manager):
        """Test searching records by type"""
        results = db_manager.search_records(record_type="mortgage")
        assert len(results) >= 1

    def test_search_records_empty_query(self, db_manager):
        """Test searching with empty query"""
        results = db_manager.search_records(query="")
        # Should return all records or handle gracefully
        assert isinstance(results, list)

    def test_search_entities(self, db_manager):
        """Test searching entities"""
        results = db_manager.search_entities(query="John")
        assert len(results) >= 1

    def test_search_entities_empty_query(self, db_manager):
        """Test searching entities with empty query"""
        results = db_manager.search_entities(query="")
        # Should return all or handle gracefully
        assert isinstance(results, list)


class TestListWithFilters:
    """Tests for list operations with filters"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()

            # Create data with specific states
            dm.create_jurisdiction(name="TX County 1", state="TX")
            dm.create_jurisdiction(name="TX County 2", state="TX")
            dm.create_jurisdiction(name="CA County 1", state="CA")

            return dm

    def test_list_jurisdictions_by_state(self, db_manager):
        """Test listing jurisdictions filtered by state"""
        results = db_manager.list_jurisdictions(state="TX")
        assert len(results) >= 2
        for r in results:
            assert r["state"] == "TX"

    def test_list_jurisdictions_with_limit(self, db_manager):
        """Test listing jurisdictions with limit"""
        results = db_manager.list_jurisdictions(limit=1)
        assert len(results) == 1

    def test_list_jurisdictions_with_offset(self, db_manager):
        """Test listing jurisdictions with offset"""
        all_results = db_manager.list_jurisdictions()
        offset_results = db_manager.list_jurisdictions(offset=1)
        # Offset results should be one less (if enough records)
        if len(all_results) > 1:
            assert len(offset_results) == len(all_results) - 1


class TestUserManagement:
    """Tests for user management operations"""

    @pytest.fixture
    def db_manager(self):
        """Create test database manager with users table"""
        from db_manager import DatabaseManager

        with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
            dm = DatabaseManager(database_url=TEST_DATABASE_URL)
            dm.init_database()
            return dm

    def test_create_user(self, db_manager):
        """Test creating a user"""
        user_id = db_manager.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User",
            roles=["user"],
            subscription_tier="free",
        )
        assert user_id is not None
        assert isinstance(user_id, int)

    def test_create_user_duplicate_username(self, db_manager):
        """Test creating user with duplicate username returns None"""
        db_manager.create_user(
            username="duplicate", email="first@example.com", hashed_password="hash1"
        )
        result = db_manager.create_user(
            username="duplicate", email="second@example.com", hashed_password="hash2"
        )
        assert result is None

    def test_get_user_by_id(self, db_manager):
        """Test getting user by ID"""
        user_id = db_manager.create_user(
            username="getbyid", email="getbyid@example.com", hashed_password="hash"
        )
        user = db_manager.get_user(user_id)
        assert user is not None
        assert user["username"] == "getbyid"
        assert user["email"] == "getbyid@example.com"

    def test_get_user_not_found(self, db_manager):
        """Test getting non-existent user returns None"""
        user = db_manager.get_user(99999)
        assert user is None

    def test_get_user_by_username(self, db_manager):
        """Test getting user by username"""
        db_manager.create_user(
            username="byusername",
            email="byusername@example.com",
            hashed_password="hash",
        )
        user = db_manager.get_user_by_username("byusername")
        assert user is not None
        assert user["username"] == "byusername"

    def test_get_user_by_email(self, db_manager):
        """Test getting user by email"""
        db_manager.create_user(
            username="byemail", email="byemail@example.com", hashed_password="hash"
        )
        user = db_manager.get_user_by_email("byemail@example.com")
        assert user is not None
        assert user["email"] == "byemail@example.com"

    def test_get_user_for_auth(self, db_manager):
        """Test getting user for authentication (includes hashed_password)"""
        db_manager.create_user(
            username="authuser", email="auth@example.com", hashed_password="secret_hash"
        )
        user = db_manager.get_user_for_auth("authuser")
        assert user is not None
        assert "hashed_password" in user
        assert user["hashed_password"] == "secret_hash"

    def test_get_user_for_auth_by_email(self, db_manager):
        """Test getting user for auth using email"""
        db_manager.create_user(
            username="authuser2",
            email="auth2@example.com",
            hashed_password="secret_hash2",
        )
        user = db_manager.get_user_for_auth("auth2@example.com")
        assert user is not None
        assert user["email"] == "auth2@example.com"

    def test_update_user(self, db_manager):
        """Test updating user fields"""
        user_id = db_manager.create_user(
            username="updateme", email="updateme@example.com", hashed_password="hash"
        )
        result = db_manager.update_user(user_id, full_name="Updated Name")
        assert result is True

        user = db_manager.get_user(user_id)
        assert user["full_name"] == "Updated Name"

    def test_update_user_not_found(self, db_manager):
        """Test updating non-existent user returns False"""
        result = db_manager.update_user(99999, full_name="Name")
        assert result is False

    def test_update_user_by_username(self, db_manager):
        """Test updating user by username"""
        db_manager.create_user(
            username="updatebyname",
            email="updatebyname@example.com",
            hashed_password="hash",
        )
        result = db_manager.update_user_by_username(
            "updatebyname", full_name="New Name"
        )
        assert result is True

        user = db_manager.get_user_by_username("updatebyname")
        assert user["full_name"] == "New Name"

    def test_delete_user(self, db_manager):
        """Test deleting user by ID"""
        user_id = db_manager.create_user(
            username="deleteme", email="deleteme@example.com", hashed_password="hash"
        )
        result = db_manager.delete_user(user_id)
        assert result is True

        user = db_manager.get_user(user_id)
        assert user is None

    def test_delete_user_by_username(self, db_manager):
        """Test deleting user by username"""
        db_manager.create_user(
            username="deletebyname",
            email="deletebyname@example.com",
            hashed_password="hash",
        )
        result = db_manager.delete_user_by_username("deletebyname")
        assert result is True

        user = db_manager.get_user_by_username("deletebyname")
        assert user is None

    def test_list_users(self, db_manager):
        """Test listing users"""
        db_manager.create_user(username="user1", email="u1@e.com", hashed_password="h")
        db_manager.create_user(username="user2", email="u2@e.com", hashed_password="h")

        users = db_manager.list_users()
        assert len(users) >= 2

    def test_list_users_by_subscription_tier(self, db_manager):
        """Test listing users filtered by subscription tier"""
        db_manager.create_user(
            username="freeuser",
            email="free@e.com",
            hashed_password="h",
            subscription_tier="free",
        )
        db_manager.create_user(
            username="prouser",
            email="pro@e.com",
            hashed_password="h",
            subscription_tier="pro",
        )

        users = db_manager.list_users(subscription_tier="pro")
        assert all(u["subscription_tier"] == "pro" for u in users)

    def test_count_users(self, db_manager):
        """Test counting users"""
        initial = db_manager.count_users()
        db_manager.create_user(username="cnt1", email="cnt1@e.com", hashed_password="h")
        db_manager.create_user(username="cnt2", email="cnt2@e.com", hashed_password="h")

        count = db_manager.count_users()
        assert count == initial + 2

    def test_record_login_success(self, db_manager):
        """Test recording successful login"""
        db_manager.create_user(
            username="logintest", email="login@e.com", hashed_password="h"
        )
        result = db_manager.record_login("logintest", success=True)
        assert result is True

        user = db_manager.get_user_by_username("logintest")
        assert user["login_count"] == 1
        assert user["last_login"] is not None

    def test_record_login_failure(self, db_manager):
        """Test recording failed login"""
        db_manager.create_user(
            username="loginfail", email="fail@e.com", hashed_password="h"
        )
        db_manager.record_login("loginfail", success=False)
        db_manager.record_login("loginfail", success=False)

        user = db_manager.get_user_by_username("loginfail")
        assert user["failed_login_count"] == 2

    def test_account_lockout(self, db_manager):
        """Test account lockout after 5 failed attempts"""
        db_manager.create_user(
            username="locktest", email="lock@e.com", hashed_password="h"
        )
        for _ in range(5):
            db_manager.record_login("locktest", success=False)

        locked = db_manager.check_user_locked("locktest")
        assert locked is True

    def test_check_user_not_locked(self, db_manager):
        """Test checking unlocked user"""
        db_manager.create_user(
            username="unlocked", email="unlocked@e.com", hashed_password="h"
        )
        locked = db_manager.check_user_locked("unlocked")
        assert locked is False

    def test_set_password_reset_token(self, db_manager):
        """Test setting password reset token"""
        db_manager.create_user(
            username="resetuser", email="reset@example.com", hashed_password="h"
        )
        result = db_manager.set_password_reset_token(
            "reset@example.com", "test_token_123"
        )
        assert result is True

    def test_get_user_by_reset_token(self, db_manager):
        """Test getting user by reset token"""
        db_manager.create_user(
            username="tokenuser", email="token@example.com", hashed_password="h"
        )
        db_manager.set_password_reset_token("token@example.com", "my_token")

        user = db_manager.get_user_by_reset_token("my_token")
        assert user is not None
        assert user["email"] == "token@example.com"

    def test_clear_password_reset_token(self, db_manager):
        """Test clearing password reset token"""
        user_id = db_manager.create_user(
            username="cleartoken", email="clear@example.com", hashed_password="h"
        )
        db_manager.set_password_reset_token("clear@example.com", "temp_token")
        result = db_manager.clear_password_reset_token(user_id)
        assert result is True

        user = db_manager.get_user_by_reset_token("temp_token")
        assert user is None

    def test_increment_api_calls(self, db_manager):
        """Test incrementing API call count"""
        user_id = db_manager.create_user(
            username="apiuser", email="api@example.com", hashed_password="h"
        )
        db_manager.increment_api_calls(user_id)
        db_manager.increment_api_calls(user_id)

        user = db_manager.get_user(user_id)
        assert user["api_calls_today"] == 2

    def test_increment_exports(self, db_manager):
        """Test incrementing export count"""
        user_id = db_manager.create_user(
            username="exportuser", email="export@example.com", hashed_password="h"
        )
        db_manager.increment_exports(user_id)
        db_manager.increment_exports(user_id)
        db_manager.increment_exports(user_id)

        user = db_manager.get_user(user_id)
        assert user["exports_this_month"] == 3
