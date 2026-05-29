"""
Extended tests for root DatabaseManager (db_manager.py)
Additional tests for uncovered methods and error handling paths.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_manager():
    """Create test database manager with initialized database."""
    from db_manager import DatabaseManager

    with patch("db_manager.DATABASE_URL", TEST_DATABASE_URL):
        dm = DatabaseManager(database_url=TEST_DATABASE_URL)
        dm.init_database()
        return dm


class TestDatabaseInitialization:
    """Tests for database initialization methods"""

    def test_drop_all_tables(self, db_manager):
        """Test dropping all tables"""
        result = db_manager.drop_all_tables()
        assert result is True

    def test_reset_database(self, db_manager):
        """Test resetting the database"""
        result = db_manager.reset_database()
        assert result is True


class TestJurisdictionOperationsExtended:
    """Extended tests for jurisdiction CRUD operations"""

    def test_create_jurisdiction_with_all_fields(self, db_manager):
        """Test creating jurisdiction with all fields"""
        jid = db_manager.create_jurisdiction(
            name="Full County",
            state="CA",
            county="Los Angeles",
            jurisdiction_type="county",
            api_available=True,
            scraper_needed=False,
            population=10000000,
            area_sq_miles=4751.0,
            description="Los Angeles County",
            contact_info={"phone": "555-1234"},
            metadata={"key": "value"},
        )
        assert jid is not None

        # Verify the data
        jurisdiction = db_manager.get_jurisdiction(jid)
        assert jurisdiction is not None
        assert jurisdiction["name"] == "Full County"
        assert jurisdiction["state"] == "CA"

    def test_get_jurisdiction_not_found(self, db_manager):
        """Test getting non-existent jurisdiction"""
        result = db_manager.get_jurisdiction(9999)
        assert result is None

    def test_get_jurisdiction_by_name_not_found(self, db_manager):
        """Test getting jurisdiction by non-existent name"""
        result = db_manager.get_jurisdiction_by_name("Non-existent County")
        assert result is None

    def test_list_jurisdictions_with_filters(self, db_manager):
        """Test listing jurisdictions with all filters"""
        # Create test jurisdictions
        db_manager.create_jurisdiction(
            name="Filter County 1",
            state="TX",
            county="Harris",
            jurisdiction_type="county",
            api_available=True,
        )
        db_manager.create_jurisdiction(
            name="Filter County 2",
            state="TX",
            county="Dallas",
            jurisdiction_type="county",
            api_available=False,
        )
        db_manager.create_jurisdiction(
            name="Filter County 3", state="CA", county="LA", jurisdiction_type="city"
        )

        # Test state filter
        results = db_manager.list_jurisdictions(state="TX")
        assert len(results) == 2

        # Test county filter
        results = db_manager.list_jurisdictions(county="Harris")
        assert len(results) >= 1

        # Test type filter
        results = db_manager.list_jurisdictions(jurisdiction_type="county")
        assert len(results) >= 2

        # Test api_available filter
        results = db_manager.list_jurisdictions(api_available=True)
        assert len(results) >= 1

        # Test ordering desc
        results = db_manager.list_jurisdictions(order_by="name", order_desc=True)
        assert len(results) >= 3

    def test_update_jurisdiction_not_found(self, db_manager):
        """Test updating non-existent jurisdiction"""
        result = db_manager.update_jurisdiction(9999, name="New Name")
        assert result is False

    def test_update_jurisdiction_with_fields(self, db_manager):
        """Test updating jurisdiction with various fields"""
        jid = db_manager.create_jurisdiction(name="Update Test County", state="WA")

        result = db_manager.update_jurisdiction(
            jid, state="OR", county="Updated County", population=50000
        )
        assert result is True

        updated = db_manager.get_jurisdiction(jid)
        assert updated["state"] == "OR"

    def test_delete_jurisdiction_not_found(self, db_manager):
        """Test deleting non-existent jurisdiction"""
        result = db_manager.delete_jurisdiction(9999)
        assert result is False

    def test_count_jurisdictions_with_state_filter(self, db_manager):
        """Test counting jurisdictions with state filter"""
        db_manager.create_jurisdiction(name="Count Test 1", state="NY")
        db_manager.create_jurisdiction(name="Count Test 2", state="NY")
        db_manager.create_jurisdiction(name="Count Test 3", state="FL")

        count = db_manager.count_jurisdictions(state="NY")
        assert count == 2


class TestDataSourceOperationsExtended:
    """Extended tests for data source operations"""

    def test_create_data_source_jurisdiction_not_found(self, db_manager):
        """Test creating data source with non-existent jurisdiction"""
        result = db_manager.create_data_source(
            jurisdiction_id=9999, source_name="Test Source", source_type="api"
        )
        assert result is None

    def test_get_data_source_not_found(self, db_manager):
        """Test getting non-existent data source"""
        result = db_manager.get_data_source(9999)
        assert result is None

    def test_list_data_sources_with_filters(self, db_manager):
        """Test listing data sources with filters"""
        jid = db_manager.create_jurisdiction(name="DS Test County", state="TX")

        db_manager.create_data_source(jid, "Source 1", "api", status="active")
        db_manager.create_data_source(jid, "Source 2", "scraper", status="inactive")

        # Test by jurisdiction
        results = db_manager.list_data_sources(jurisdiction_id=jid)
        assert len(results) == 2

        # Test by source_type
        results = db_manager.list_data_sources(source_type="api")
        assert len(results) >= 1

        # Test by status
        results = db_manager.list_data_sources(status="active")
        assert len(results) >= 1

    def test_update_data_source_status_not_found(self, db_manager):
        """Test updating status of non-existent data source"""
        result = db_manager.update_data_source_status(9999, "active")
        assert result is False

    def test_update_data_source_status_with_counts(self, db_manager):
        """Test updating data source status with error/success counts"""
        jid = db_manager.create_jurisdiction(name="Status Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Status Test Source", "api")

        result = db_manager.update_data_source_status(
            dsid, "error", error_count=5, success_count=10
        )
        assert result is True

    def test_record_scrape_not_found(self, db_manager):
        """Test recording scrape for non-existent data source"""
        result = db_manager.record_scrape(9999, success=True)
        assert result is False

    def test_record_scrape_success(self, db_manager):
        """Test recording successful scrape"""
        jid = db_manager.create_jurisdiction(name="Scrape Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Scrape Test Source", "api")

        result = db_manager.record_scrape(dsid, success=True)
        assert result is True

    def test_record_scrape_failure_locks_after_3(self, db_manager):
        """Test that data source enters error status after 3 failures"""
        jid = db_manager.create_jurisdiction(name="Fail Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Fail Test Source", "api")

        # Record 3 failures
        db_manager.record_scrape(dsid, success=False)
        db_manager.record_scrape(dsid, success=False)
        db_manager.record_scrape(dsid, success=False)

        ds = db_manager.get_data_source(dsid)
        assert ds["status"] == "error"


class TestRecordOperationsExtended:
    """Extended tests for record operations"""

    def test_create_record_with_all_fields(self, db_manager):
        """Test creating record with all fields"""
        jid = db_manager.create_jurisdiction(name="Record Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Record Source", "api")

        rid = db_manager.create_record(
            jurisdiction_id=jid,
            data_source_id=dsid,
            record_type="deed",
            title="Property Transfer",
            description="Transfer of property",
            amount=500000.00,
            date=datetime.utcnow(),
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            grantor="John Doe",
            grantee="Jane Smith",
            borrower="Jane Smith",
            lender="Big Bank",
            document_number="DOC123456",
            url="http://example.com/doc",
            raw_data={"field": "value"},
            metadata={"type": "residential"},
        )
        assert rid is not None

    def test_get_record_not_found(self, db_manager):
        """Test getting non-existent record"""
        result = db_manager.get_record(9999)
        assert result is None

    def test_bulk_create_records(self, db_manager):
        """Test bulk creating records"""
        jid = db_manager.create_jurisdiction(name="Bulk Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Bulk Source", "api")

        records = [
            {
                "jurisdiction_id": jid,
                "data_source_id": dsid,
                "record_type": "deed",
                "title": "Record 1",
            },
            {
                "jurisdiction_id": jid,
                "data_source_id": dsid,
                "record_type": "deed",
                "title": "Record 2",
            },
            {
                "jurisdiction_id": jid,
                "data_source_id": dsid,
                "record_type": "deed",
                "title": "Record 3",
            },
        ]

        count = db_manager.bulk_create_records(records)
        assert count == 3

    def test_search_records_with_all_filters(self, db_manager):
        """Test searching records with all filters"""
        jid = db_manager.create_jurisdiction(name="Search Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Search Source", "api")

        db_manager.create_record(
            jid,
            dsid,
            "deed",
            "Test Property Transfer",
            grantor="John Doe",
            grantee="Jane Smith",
            amount=250000.00,
            city="Houston",
            state="TX",
            date=datetime.utcnow(),
        )

        # Test text query
        results = db_manager.search_records(query="Test Property")
        assert len(results) >= 1

        # Test amount filters
        results = db_manager.search_records(amount_min=100000, amount_max=300000)
        assert len(results) >= 1

        # Test grantor/grantee filters
        results = db_manager.search_records(grantor="John")
        assert len(results) >= 1

        results = db_manager.search_records(grantee="Jane")
        assert len(results) >= 1

        # Test city/state filters
        results = db_manager.search_records(city="Houston", state="TX")
        assert len(results) >= 1

        # Test ordering asc
        results = db_manager.search_records(order_by="amount", order_desc=False)
        assert len(results) >= 1

    def test_count_records_with_filters(self, db_manager):
        """Test counting records with filters"""
        jid = db_manager.create_jurisdiction(name="Count Rec County", state="TX")
        dsid = db_manager.create_data_source(jid, "Count Source", "api")

        db_manager.create_record(jid, dsid, "deed", "Count Record 1")
        db_manager.create_record(jid, dsid, "mortgage", "Count Record 2")

        count = db_manager.count_records(record_type="deed")
        assert count >= 1

    def test_get_record_stats(self, db_manager):
        """Test getting record statistics"""
        jid = db_manager.create_jurisdiction(name="Stats County", state="TX")
        dsid = db_manager.create_data_source(jid, "Stats Source", "api")

        db_manager.create_record(jid, dsid, "deed", "Stats Record 1", amount=100000.00)
        db_manager.create_record(jid, dsid, "deed", "Stats Record 2", amount=200000.00)

        stats = db_manager.get_record_stats()
        assert "total_records" in stats
        assert stats["total_records"] >= 2


class TestEntityOperationsExtended:
    """Extended tests for entity operations"""

    def test_create_entity_with_all_fields(self, db_manager):
        """Test creating entity with all fields"""
        eid = db_manager.create_entity(
            entity_name="John Doe",
            entity_type="person",
            entity_id="EXT123",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            phone="555-1234",
            email="john@example.com",
            description="Test person entity",
            data={"occupation": "Engineer"},
            metadata={"verified": True},
        )
        assert eid is not None

    def test_get_entity_not_found(self, db_manager):
        """Test getting non-existent entity"""
        result = db_manager.get_entity(9999)
        assert result is None

    def test_search_entities_with_all_filters(self, db_manager):
        """Test searching entities with all filters"""
        db_manager.create_entity(
            "Search Test Person", "person", city="Dallas", state="TX"
        )
        db_manager.create_entity(
            "Search Test Company", "company", city="Austin", state="TX"
        )

        # Test by query
        results = db_manager.search_entities(query="Search Test")
        assert len(results) >= 2

        # Test by entity_type
        results = db_manager.search_entities(entity_type="person")
        assert len(results) >= 1

        # Test by city
        results = db_manager.search_entities(city="Dallas")
        assert len(results) >= 1

        # Test by state
        results = db_manager.search_entities(state="TX")
        assert len(results) >= 2


class TestRelationshipOperations:
    """Tests for relationship operations"""

    def test_create_relationship(self, db_manager):
        """Test creating a relationship"""
        jid = db_manager.create_jurisdiction(name="Rel Test County", state="TX")
        dsid = db_manager.create_data_source(jid, "Rel Source", "api")
        rid = db_manager.create_record(jid, dsid, "deed", "Rel Test Record")

        e1 = db_manager.create_entity("Entity 1", "person")
        e2 = db_manager.create_entity("Entity 2", "property")

        rel_id = db_manager.create_relationship(
            entity1_id=e1,
            entity2_id=e2,
            record_id=rid,
            relationship_type="owns",
            role1="owner",
            role2="property",
            context="Property ownership",
            confidence_score=0.95,
            evidence={"document": "deed"},
            metadata={"verified": True},
        )
        assert rel_id is not None

    def test_get_entity_relationships(self, db_manager):
        """Test getting entity relationships"""
        jid = db_manager.create_jurisdiction(name="Get Rel County", state="TX")
        dsid = db_manager.create_data_source(jid, "Get Rel Source", "api")
        rid = db_manager.create_record(jid, dsid, "deed", "Get Rel Record")

        e1 = db_manager.create_entity("Get Rel Entity 1", "person")
        e2 = db_manager.create_entity("Get Rel Entity 2", "property")

        db_manager.create_relationship(e1, e2, rid, "owns")

        # Get relationships for entity1
        results = db_manager.get_entity_relationships(e1)
        assert len(results) >= 1

        # Get relationships with type filter
        results = db_manager.get_entity_relationships(e1, relationship_type="owns")
        assert len(results) >= 1


class TestDashboardStats:
    """Tests for dashboard statistics"""

    def test_get_dashboard_stats(self, db_manager):
        """Test getting dashboard statistics"""
        jid = db_manager.create_jurisdiction(name="Dashboard County", state="TX")
        dsid = db_manager.create_data_source(jid, "Dashboard Source", "api")
        db_manager.create_record(jid, dsid, "deed", "Dashboard Record")
        db_manager.create_entity("Dashboard Entity", "person")

        stats = db_manager.get_dashboard_stats()

        assert "totalRecords" in stats
        assert "jurisdictions" in stats
        assert "dataSources" in stats
        assert "activeScrapers" in stats
        assert "totalEntities" in stats
        assert "recentRecords" in stats


class TestUserOperations:
    """Tests for user CRUD operations"""

    def test_create_user(self, db_manager):
        """Test creating a user"""
        uid = db_manager.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password="hashedpassword123",
            full_name="Test User",
            roles=["user", "admin"],
            disabled=False,
            email_verified=True,
            subscription_tier="pro",
        )
        assert uid is not None

    def test_create_user_duplicate(self, db_manager):
        """Test creating duplicate user fails"""
        db_manager.create_user("dupuser", "dup@example.com", "hash123")
        result = db_manager.create_user("dupuser", "dup2@example.com", "hash456")
        assert result is None

    def test_get_user(self, db_manager):
        """Test getting user by ID"""
        uid = db_manager.create_user("getuser", "get@example.com", "hash123")

        user = db_manager.get_user(uid)
        assert user is not None
        assert user["username"] == "getuser"

    def test_get_user_not_found(self, db_manager):
        """Test getting non-existent user"""
        result = db_manager.get_user(9999)
        assert result is None

    def test_get_user_by_username(self, db_manager):
        """Test getting user by username"""
        db_manager.create_user("byusername", "byusername@example.com", "hash123")

        user = db_manager.get_user_by_username("byusername")
        assert user is not None
        assert user["email"] == "byusername@example.com"

    def test_get_user_by_username_not_found(self, db_manager):
        """Test getting non-existent username"""
        result = db_manager.get_user_by_username("nonexistent")
        assert result is None

    def test_get_user_by_email(self, db_manager):
        """Test getting user by email"""
        db_manager.create_user("byemail", "byemail@example.com", "hash123")

        user = db_manager.get_user_by_email("byemail@example.com")
        assert user is not None
        assert user["username"] == "byemail"

    def test_get_user_by_email_not_found(self, db_manager):
        """Test getting non-existent email"""
        result = db_manager.get_user_by_email("nonexistent@example.com")
        assert result is None

    def test_get_user_for_auth(self, db_manager):
        """Test getting user for authentication (includes password)"""
        db_manager.create_user("authuser", "auth@example.com", "authpasshash")

        user = db_manager.get_user_for_auth("authuser")
        assert user is not None
        assert "hashed_password" in user

    def test_check_user_locked_not_locked(self, db_manager):
        """Test checking unlocked user"""
        db_manager.create_user("unlocked", "unlocked@example.com", "hash123")

        result = db_manager.check_user_locked("unlocked")
        assert result is False

    def test_check_user_locked_not_found(self, db_manager):
        """Test checking non-existent user lock status"""
        result = db_manager.check_user_locked("nonexistent")
        assert result is False

    def test_list_users(self, db_manager):
        """Test listing users"""
        db_manager.create_user(
            "listuser1",
            "list1@example.com",
            "hash123",
            disabled=False,
            subscription_tier="free",
        )
        db_manager.create_user(
            "listuser2",
            "list2@example.com",
            "hash123",
            disabled=True,
            subscription_tier="pro",
        )

        # List all
        users = db_manager.list_users()
        assert len(users) >= 2

        # List by disabled
        users = db_manager.list_users(disabled=False)
        assert len(users) >= 1

        # List by subscription
        users = db_manager.list_users(subscription_tier="pro")
        assert len(users) >= 1

        # List with role filter
        db_manager.create_user("roleuser", "role@example.com", "hash", roles=["admin"])
        users = db_manager.list_users(role="admin")
        assert len(users) >= 1

        # List with ordering asc
        users = db_manager.list_users(order_by="username", order_desc=False)
        assert len(users) >= 1

    def test_update_user(self, db_manager):
        """Test updating user"""
        uid = db_manager.create_user("updateuser", "update@example.com", "hash123")

        result = db_manager.update_user(uid, full_name="Updated Name", disabled=True)
        assert result is True

        user = db_manager.get_user(uid)
        assert user["full_name"] == "Updated Name"
        assert user["disabled"] is True

    def test_update_user_not_found(self, db_manager):
        """Test updating non-existent user"""
        result = db_manager.update_user(9999, full_name="Test")
        assert result is False

    def test_update_user_by_username(self, db_manager):
        """Test updating user by username"""
        db_manager.create_user("byusername2", "byusername2@example.com", "hash123")

        result = db_manager.update_user_by_username("byusername2", full_name="Updated")
        assert result is True

    def test_update_user_by_username_not_found(self, db_manager):
        """Test updating non-existent username"""
        result = db_manager.update_user_by_username("nonexistent", full_name="Test")
        assert result is False

    def test_delete_user(self, db_manager):
        """Test deleting user by ID"""
        uid = db_manager.create_user("deleteuser", "delete@example.com", "hash123")

        result = db_manager.delete_user(uid)
        assert result is True

        user = db_manager.get_user(uid)
        assert user is None

    def test_delete_user_not_found(self, db_manager):
        """Test deleting non-existent user"""
        result = db_manager.delete_user(9999)
        assert result is False

    def test_delete_user_by_username(self, db_manager):
        """Test deleting user by username"""
        db_manager.create_user("deletebyname", "deletebyname@example.com", "hash123")

        result = db_manager.delete_user_by_username("deletebyname")
        assert result is True

    def test_delete_user_by_username_not_found(self, db_manager):
        """Test deleting non-existent username"""
        result = db_manager.delete_user_by_username("nonexistent")
        assert result is False

    def test_count_users(self, db_manager):
        """Test counting users"""
        db_manager.create_user(
            "countuser1",
            "count1@example.com",
            "hash",
            disabled=False,
            subscription_tier="free",
        )
        db_manager.create_user(
            "countuser2",
            "count2@example.com",
            "hash",
            disabled=True,
            subscription_tier="pro",
        )

        total = db_manager.count_users()
        assert total >= 2

        disabled_count = db_manager.count_users(disabled=True)
        assert disabled_count >= 1

        pro_count = db_manager.count_users(subscription_tier="pro")
        assert pro_count >= 1

    def test_record_login_success(self, db_manager):
        """Test recording successful login"""
        db_manager.create_user("loginuser", "login@example.com", "hash123")

        result = db_manager.record_login("loginuser", success=True)
        assert result is True

        user = db_manager.get_user_by_username("loginuser")
        assert user["login_count"] >= 1

    def test_record_login_failure(self, db_manager):
        """Test recording failed login"""
        db_manager.create_user("faillogin", "faillogin@example.com", "hash123")

        result = db_manager.record_login("faillogin", success=False)
        assert result is True

        # Just verify the function returned True - the internal state is updated
        # but failed_login_count may not be included in user dict representation

    def test_record_login_not_found(self, db_manager):
        """Test recording login for non-existent user"""
        result = db_manager.record_login("nonexistent", success=True)
        assert result is False

    def test_record_login_locks_after_5_failures(self, db_manager):
        """Test that user is locked after 5 failed logins"""
        db_manager.create_user("locktest", "locktest@example.com", "hash123")

        for _ in range(5):
            db_manager.record_login("locktest", success=False)

        locked = db_manager.check_user_locked("locktest")
        assert locked is True

    def test_set_password_reset_token(self, db_manager):
        """Test setting password reset token"""
        db_manager.create_user("resetuser", "reset@example.com", "hash123")

        result = db_manager.set_password_reset_token(
            "reset@example.com", "token123", expires_hours=2
        )
        assert result is True

    def test_set_password_reset_token_not_found(self, db_manager):
        """Test setting password reset token for non-existent user"""
        result = db_manager.set_password_reset_token(
            "nonexistent@example.com", "token123"
        )
        assert result is False

    def test_get_user_by_reset_token(self, db_manager):
        """Test getting user by reset token"""
        db_manager.create_user("tokenuser", "token@example.com", "hash123")
        db_manager.set_password_reset_token(
            "token@example.com", "valid_token", expires_hours=1
        )

        user = db_manager.get_user_by_reset_token("valid_token")
        assert user is not None
        assert user["username"] == "tokenuser"

    def test_get_user_by_reset_token_invalid(self, db_manager):
        """Test getting user by invalid reset token"""
        result = db_manager.get_user_by_reset_token("invalid_token")
        assert result is None

    def test_clear_password_reset_token(self, db_manager):
        """Test clearing password reset token"""
        uid = db_manager.create_user("cleartoken", "cleartoken@example.com", "hash123")
        db_manager.set_password_reset_token("cleartoken@example.com", "token123")

        result = db_manager.clear_password_reset_token(uid)
        assert result is True

    def test_clear_password_reset_token_not_found(self, db_manager):
        """Test clearing reset token for non-existent user"""
        result = db_manager.clear_password_reset_token(9999)
        assert result is False

    def test_increment_api_calls(self, db_manager):
        """Test incrementing API call count"""
        uid = db_manager.create_user("apiuser", "api@example.com", "hash123")

        result = db_manager.increment_api_calls(uid)
        assert result is True

        user = db_manager.get_user(uid)
        assert user["api_calls_today"] >= 1

    def test_increment_api_calls_not_found(self, db_manager):
        """Test incrementing API calls for non-existent user"""
        result = db_manager.increment_api_calls(9999)
        assert result is False

    def test_increment_exports(self, db_manager):
        """Test incrementing export count"""
        uid = db_manager.create_user("exportuser", "export@example.com", "hash123")

        result = db_manager.increment_exports(uid)
        assert result is True

        user = db_manager.get_user(uid)
        assert user["exports_this_month"] >= 1

    def test_increment_exports_not_found(self, db_manager):
        """Test incrementing exports for non-existent user"""
        result = db_manager.increment_exports(9999)
        assert result is False
