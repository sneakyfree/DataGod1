"""
Comprehensive tests for DatabaseManager operations.

Tests cover:
- Jurisdiction CRUD operations
- Data Source operations
- Record operations
- Entity operations
- User operations
- Statistics and dashboard
"""

import pytest
from datetime import datetime, timedelta
from db_manager import DatabaseManager


@pytest.fixture
def db():
    """Create a DatabaseManager instance for testing."""
    db = DatabaseManager("sqlite:///:memory:")
    db.init_database()
    yield db
    db.drop_all_tables()


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_init_with_default_url(self):
        """Test initialization with default URL."""
        db = DatabaseManager("sqlite:///:memory:")
        assert db.database_url == "sqlite:///:memory:"
        assert db.engine is not None
        assert db.SessionLocal is not None

    def test_init_database(self, db):
        """Test database initialization creates tables."""
        # Tables should already be created by fixture
        # Verify by creating a jurisdiction
        jid = db.create_jurisdiction(name="Test County", state="TX")
        assert jid is not None

    def test_drop_all_tables(self):
        """Test dropping all tables."""
        db = DatabaseManager("sqlite:///:memory:")
        db.init_database()
        result = db.drop_all_tables()
        assert result is True

    def test_reset_database(self):
        """Test resetting database."""
        db = DatabaseManager("sqlite:///:memory:")
        db.init_database()
        db.create_jurisdiction(name="Test County", state="TX")

        result = db.reset_database()
        assert result is True

        # After reset, previous data should be gone
        count = db.count_jurisdictions()
        assert count == 0


class TestJurisdictionOperations:
    """Tests for Jurisdiction CRUD operations."""

    def test_create_jurisdiction(self, db):
        """Test creating a jurisdiction."""
        jid = db.create_jurisdiction(
            name="Harris County",
            state="TX",
            county="Harris",
            jurisdiction_type="county",
            api_available=True,
            population=4700000
        )

        assert jid is not None
        assert isinstance(jid, int)

    def test_create_jurisdiction_duplicate(self, db):
        """Test creating duplicate jurisdiction fails."""
        db.create_jurisdiction(name="Harris County", state="TX")
        jid2 = db.create_jurisdiction(name="Harris County", state="TX")

        assert jid2 is None  # Should fail due to duplicate

    def test_get_jurisdiction(self, db):
        """Test getting a jurisdiction by ID."""
        jid = db.create_jurisdiction(
            name="Dallas County",
            state="TX",
            population=2600000
        )

        jurisdiction = db.get_jurisdiction(jid)

        assert jurisdiction is not None
        assert jurisdiction["name"] == "Dallas County"
        assert jurisdiction["state"] == "TX"
        assert jurisdiction["population"] == 2600000

    def test_get_jurisdiction_not_found(self, db):
        """Test getting non-existent jurisdiction."""
        jurisdiction = db.get_jurisdiction(99999)
        assert jurisdiction is None

    def test_get_jurisdiction_by_name(self, db):
        """Test getting jurisdiction by name."""
        db.create_jurisdiction(name="Travis County", state="TX")

        jurisdiction = db.get_jurisdiction_by_name("Travis County")

        assert jurisdiction is not None
        assert jurisdiction["name"] == "Travis County"

    def test_get_jurisdiction_by_name_not_found(self, db):
        """Test getting non-existent jurisdiction by name."""
        jurisdiction = db.get_jurisdiction_by_name("Nonexistent County")
        assert jurisdiction is None

    def test_list_jurisdictions(self, db):
        """Test listing jurisdictions."""
        db.create_jurisdiction(name="Harris County", state="TX")
        db.create_jurisdiction(name="Dallas County", state="TX")
        db.create_jurisdiction(name="Los Angeles County", state="CA")

        jurisdictions = db.list_jurisdictions()

        assert len(jurisdictions) == 3

    def test_list_jurisdictions_filter_by_state(self, db):
        """Test filtering jurisdictions by state."""
        db.create_jurisdiction(name="Harris County", state="TX")
        db.create_jurisdiction(name="Dallas County", state="TX")
        db.create_jurisdiction(name="Los Angeles County", state="CA")

        tx_jurisdictions = db.list_jurisdictions(state="TX")

        assert len(tx_jurisdictions) == 2
        assert all(j["state"] == "TX" for j in tx_jurisdictions)

    def test_list_jurisdictions_filter_by_api_available(self, db):
        """Test filtering jurisdictions by API availability."""
        db.create_jurisdiction(name="Harris County", state="TX", api_available=True)
        db.create_jurisdiction(name="Dallas County", state="TX", api_available=False)

        api_jurisdictions = db.list_jurisdictions(api_available=True)

        assert len(api_jurisdictions) == 1
        assert api_jurisdictions[0]["name"] == "Harris County"

    def test_list_jurisdictions_pagination(self, db):
        """Test jurisdiction pagination."""
        for i in range(10):
            db.create_jurisdiction(name=f"County {i}", state="TX")

        page1 = db.list_jurisdictions(limit=5, offset=0)
        page2 = db.list_jurisdictions(limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0]["name"] != page2[0]["name"]

    def test_list_jurisdictions_ordering(self, db):
        """Test jurisdiction ordering."""
        db.create_jurisdiction(name="Zebra County", state="TX")
        db.create_jurisdiction(name="Alpha County", state="TX")

        asc_list = db.list_jurisdictions(order_by="name", order_desc=False)
        desc_list = db.list_jurisdictions(order_by="name", order_desc=True)

        assert asc_list[0]["name"] == "Alpha County"
        assert desc_list[0]["name"] == "Zebra County"

    def test_update_jurisdiction(self, db):
        """Test updating a jurisdiction."""
        jid = db.create_jurisdiction(name="Harris County", state="TX", population=1000000)

        result = db.update_jurisdiction(jid, population=4700000, api_available=True)

        assert result is True

        updated = db.get_jurisdiction(jid)
        assert updated["population"] == 4700000
        assert updated["api_available"] is True

    def test_update_jurisdiction_not_found(self, db):
        """Test updating non-existent jurisdiction."""
        result = db.update_jurisdiction(99999, population=1000)
        assert result is False

    def test_delete_jurisdiction(self, db):
        """Test deleting a jurisdiction."""
        jid = db.create_jurisdiction(name="Test County", state="TX")

        result = db.delete_jurisdiction(jid)

        assert result is True
        assert db.get_jurisdiction(jid) is None

    def test_delete_jurisdiction_not_found(self, db):
        """Test deleting non-existent jurisdiction."""
        result = db.delete_jurisdiction(99999)
        assert result is False

    def test_count_jurisdictions(self, db):
        """Test counting jurisdictions."""
        db.create_jurisdiction(name="Harris County", state="TX")
        db.create_jurisdiction(name="Dallas County", state="TX")
        db.create_jurisdiction(name="LA County", state="CA")

        total = db.count_jurisdictions()
        tx_count = db.count_jurisdictions(state="TX")

        assert total == 3
        assert tx_count == 2


class TestDataSourceOperations:
    """Tests for DataSource operations."""

    def test_create_data_source(self, db):
        """Test creating a data source."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")

        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Harris CAD API",
            source_type="api",
            api_endpoint="https://api.hcad.org/v1",
            status="active"
        )

        assert source_id is not None

    def test_create_data_source_invalid_jurisdiction(self, db):
        """Test creating data source with invalid jurisdiction."""
        source_id = db.create_data_source(
            jurisdiction_id=99999,
            source_name="Test API",
            source_type="api"
        )

        assert source_id is None

    def test_get_data_source(self, db):
        """Test getting a data source."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        source = db.get_data_source(source_id)

        assert source is not None
        assert source["source_name"] == "Test API"

    def test_list_data_sources(self, db):
        """Test listing data sources for a jurisdiction."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        db.create_data_source(jurisdiction_id=jid, source_name="API 1", source_type="api")
        db.create_data_source(jurisdiction_id=jid, source_name="API 2", source_type="api")

        sources = db.list_data_sources(jurisdiction_id=jid)

        assert len(sources) == 2

    def test_update_data_source_status(self, db):
        """Test updating data source status."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api",
            status="active"
        )

        result = db.update_data_source_status(source_id, "inactive")

        assert result is True
        source = db.get_data_source(source_id)
        assert source["status"] == "inactive"

    def test_record_scrape(self, db):
        """Test recording a scrape operation."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        # record_scrape only takes data_source_id and success (no records_count)
        result = db.record_scrape(source_id, success=True)

        assert result is True
        source = db.get_data_source(source_id)
        assert source["success_count"] >= 1


class TestRecordOperations:
    """Tests for Record operations."""

    def test_create_record(self, db):
        """Test creating a record."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        record_id = db.create_record(
            jurisdiction_id=jid,
            data_source_id=source_id,
            record_type="property",
            title="123 Main St Property",
            grantor="John Doe",
            grantee="Jane Smith",
            amount=250000.00,
            address="123 Main St",
            city="Houston",
            state="TX"
        )

        assert record_id is not None

    def test_bulk_create_records(self, db):
        """Test bulk creating records."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        records = [
            {
                "jurisdiction_id": jid,
                "data_source_id": source_id,
                "record_type": "property",
                "title": f"Property {i}",
                "grantor": "Seller",
                "grantee": "Buyer"
            }
            for i in range(10)
        ]

        count = db.bulk_create_records(records)

        assert count == 10

    def test_get_record(self, db):
        """Test getting a record by ID."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )
        record_id = db.create_record(
            jurisdiction_id=jid,
            data_source_id=source_id,
            record_type="mortgage",
            title="Test Mortgage",
            amount=500000
        )

        record = db.get_record(record_id)

        assert record is not None
        assert record["record_type"] == "mortgage"
        assert record["amount"] == 500000

    def test_search_records_by_type(self, db):
        """Test searching records by type."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Property 1")
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="mortgage", title="Mortgage 1")
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Property 2")

        results = db.search_records(record_type="property")

        assert len(results) == 2

    def test_search_records_by_grantor(self, db):
        """Test searching records by grantor name."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Prop 1", grantor="John Doe")
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Prop 2", grantor="Jane Smith")
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Prop 3", grantor="John Johnson")

        results = db.search_records(grantor="John")

        assert len(results) == 2

    def test_search_records_by_amount_range(self, db):
        """Test searching records by amount range."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="mortgage", title="M1", amount=100000)
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="mortgage", title="M2", amount=250000)
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="mortgage", title="M3", amount=500000)

        # API uses amount_min/amount_max, not min_amount/max_amount
        results = db.search_records(amount_min=200000, amount_max=300000)

        assert len(results) == 1
        assert results[0]["amount"] == 250000

    def test_count_records(self, db):
        """Test counting records."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        for i in range(5):
            db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                            record_type="property", title=f"Prop {i}")

        count = db.count_records()
        type_count = db.count_records(record_type="property")

        assert count == 5
        assert type_count == 5

    def test_get_record_stats(self, db):
        """Test getting record statistics."""
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )

        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="P1", amount=100000)
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="mortgage", title="M1", amount=500000)

        stats = db.get_record_stats()

        assert "total_records" in stats
        assert "by_type" in stats
        assert stats["total_records"] == 2


class TestEntityOperations:
    """Tests for Entity operations."""

    def test_create_entity(self, db):
        """Test creating an entity."""
        entity_id = db.create_entity(
            entity_name="Test Corporation",
            entity_type="company",
            address="123 Business Ave",
            city="Houston",
            state="TX"
        )

        assert entity_id is not None

    def test_get_entity(self, db):
        """Test getting an entity by ID."""
        entity_id = db.create_entity(
            entity_name="Test LLC",
            entity_type="company",
            city="Houston"
        )

        entity = db.get_entity(entity_id)

        assert entity is not None
        assert entity["entity_name"] == "Test LLC"

    def test_search_entities(self, db):
        """Test searching entities."""
        db.create_entity(entity_name="Acme Corp", entity_type="company")
        db.create_entity(entity_name="John Doe", entity_type="person")
        db.create_entity(entity_name="Acme LLC", entity_type="company")

        # API uses query parameter, not name
        results = db.search_entities(query="Acme")

        assert len(results) == 2


class TestUserOperations:
    """Tests for User operations."""

    def test_create_user(self, db):
        """Test creating a user."""
        user_id = db.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User"
        )

        assert user_id is not None

    def test_create_user_duplicate_username(self, db):
        """Test creating user with duplicate username fails."""
        db.create_user(username="testuser", email="test1@example.com",
                      hashed_password="hash1")
        user_id = db.create_user(username="testuser", email="test2@example.com",
                                hashed_password="hash2")

        assert user_id is None

    def test_create_user_duplicate_email(self, db):
        """Test creating user with duplicate email fails."""
        db.create_user(username="user1", email="test@example.com",
                      hashed_password="hash1")
        user_id = db.create_user(username="user2", email="test@example.com",
                                hashed_password="hash2")

        assert user_id is None

    def test_get_user(self, db):
        """Test getting a user by ID."""
        user_id = db.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User"
        )

        user = db.get_user(user_id)

        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert "hashed_password" not in user  # Should not include password

    def test_get_user_by_username(self, db):
        """Test getting a user by username."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        user = db.get_user_by_username("testuser")

        assert user is not None
        assert user["username"] == "testuser"

    def test_get_user_by_email(self, db):
        """Test getting a user by email."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        user = db.get_user_by_email("test@example.com")

        assert user is not None
        assert user["email"] == "test@example.com"

    def test_get_user_for_auth(self, db):
        """Test getting user for authentication (includes password)."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hashed_password_123")

        user = db.get_user_for_auth("testuser")

        assert user is not None
        assert "hashed_password" in user
        assert user["hashed_password"] == "hashed_password_123"

    def test_update_user(self, db):
        """Test updating a user."""
        user_id = db.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User"
        )

        result = db.update_user(user_id, full_name="Updated Name")

        assert result is True
        user = db.get_user(user_id)
        assert user["full_name"] == "Updated Name"

    def test_delete_user(self, db):
        """Test deleting a user."""
        user_id = db.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hash"
        )

        result = db.delete_user(user_id)

        assert result is True
        assert db.get_user(user_id) is None

    def test_record_login_success(self, db):
        """Test recording successful login."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        result = db.record_login("testuser", success=True)

        assert result is True
        user = db.get_user_by_username("testuser")
        # _user_to_dict returns login_count, not failed_login_count
        assert user["login_count"] >= 1

    def test_record_login_failure(self, db):
        """Test recording failed login attempts (account lockout)."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        # Record 3 failed logins
        for _ in range(3):
            db.record_login("testuser", success=False)

        # User should not be locked yet (needs 5 failures)
        assert db.check_user_locked("testuser") is False

        # Record 2 more failed logins to trigger lockout
        for _ in range(2):
            db.record_login("testuser", success=False)

        # Now user should be locked
        assert db.check_user_locked("testuser") is True

    def test_check_user_locked(self, db):
        """Test checking if user is locked."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        # User should not be locked initially
        assert db.check_user_locked("testuser") is False

        # Record 5 failed logins to trigger lockout
        for _ in range(5):
            db.record_login("testuser", success=False)

        # User should now be locked
        assert db.check_user_locked("testuser") is True

    def test_set_password_reset_token(self, db):
        """Test setting password reset token."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        result = db.set_password_reset_token("test@example.com", "reset-token-123")

        assert result is True

    def test_get_user_by_reset_token(self, db):
        """Test getting user by reset token."""
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")
        db.set_password_reset_token("test@example.com", "reset-token-123")

        user = db.get_user_by_reset_token("reset-token-123")

        assert user is not None
        assert user["username"] == "testuser"

    def test_clear_password_reset_token(self, db):
        """Test clearing password reset token."""
        user_id = db.create_user(username="testuser", email="test@example.com",
                                hashed_password="hash")
        db.set_password_reset_token("test@example.com", "reset-token-123")

        result = db.clear_password_reset_token(user_id)

        assert result is True
        user = db.get_user_by_reset_token("reset-token-123")
        assert user is None

    def test_count_users(self, db):
        """Test counting users."""
        db.create_user(username="user1", email="user1@example.com",
                      hashed_password="hash", subscription_tier="free")
        db.create_user(username="user2", email="user2@example.com",
                      hashed_password="hash", subscription_tier="pro")
        db.create_user(username="user3", email="user3@example.com",
                      hashed_password="hash", subscription_tier="free")

        total = db.count_users()
        free_count = db.count_users(subscription_tier="free")

        assert total == 3
        assert free_count == 2


class TestDashboardStats:
    """Tests for dashboard statistics."""

    def test_get_dashboard_stats(self, db):
        """Test getting dashboard statistics."""
        # Create some test data
        jid = db.create_jurisdiction(name="Harris County", state="TX")
        source_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Test API",
            source_type="api"
        )
        db.create_record(jurisdiction_id=jid, data_source_id=source_id,
                        record_type="property", title="Test")
        db.create_entity(entity_name="Test Corp", entity_type="company")
        db.create_user(username="testuser", email="test@example.com",
                      hashed_password="hash")

        stats = db.get_dashboard_stats()

        # API uses camelCase keys: totalRecords, jurisdictions, etc.
        assert "totalRecords" in stats
        assert "jurisdictions" in stats
        assert "dataSources" in stats
        assert "activeScrapers" in stats
        assert "totalEntities" in stats
        assert "recentRecords" in stats
        assert stats["jurisdictions"] >= 1
        assert stats["totalRecords"] >= 1


class TestSessionManagement:
    """Tests for session management."""

    def test_get_session_context_manager(self, db):
        """Test session context manager."""
        with db.get_session() as session:
            assert session is not None
            # Session should be active
            from datagod.models import Jurisdiction
            count = session.query(Jurisdiction).count()
            assert count >= 0

    def test_session_rollback_on_error(self, db):
        """Test that session rolls back on error."""
        jid = db.create_jurisdiction(name="Original", state="TX")

        try:
            with db.get_session() as session:
                from datagod.models import Jurisdiction
                j = session.query(Jurisdiction).filter_by(id=jid).first()
                j.name = "Modified"
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Original name should be preserved due to rollback
        j = db.get_jurisdiction(jid)
        assert j["name"] == "Original"
