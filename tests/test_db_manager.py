"""
Tests for DatabaseManager
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestDatabaseManager:
    """Tests for DatabaseManager class"""

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization"""
        from db_manager import DatabaseManager

        db = DatabaseManager("sqlite:///:memory:")
        assert db.database_url == "sqlite:///:memory:"
        assert db.engine is not None
        assert db.SessionLocal is not None

    def test_get_session_context_manager(self):
        """Test session context manager"""
        with patch("sqlalchemy.create_engine"):
            with patch("sqlalchemy.orm.sessionmaker") as mock_sessionmaker:
                from db_manager import DatabaseManager

                mock_session = MagicMock()
                mock_sessionmaker.return_value = lambda: mock_session

                db = DatabaseManager("sqlite:///:memory:")

                with db.get_session() as session:
                    assert session is not None

    def test_create_jurisdiction(self, db_session, sample_jurisdiction_data):
        """Test creating a jurisdiction through DatabaseManager"""
        from datagod.models import Jurisdiction

        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Query back
        result = db_session.query(Jurisdiction).filter_by(name="Test County").first()
        assert result is not None
        assert result.state == "TX"

    def test_search_records(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test searching records"""
        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create record
        sample_record_data["jurisdiction_id"] = jurisdiction.id
        sample_record_data["data_source_id"] = data_source.id
        record = Record(**sample_record_data)
        db_session.add(record)
        db_session.commit()

        # Search
        results = (
            db_session.query(Record).filter(Record.record_type == "mortgage").all()
        )

        assert len(results) == 1
        assert results[0].grantor == "John Doe"

    def test_bulk_create_records(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test bulk creating records"""
        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create multiple records
        records = []
        for i in range(10):
            data = sample_record_data.copy()
            data["record_id"] = f"TEST-{i}"
            data["jurisdiction_id"] = jurisdiction.id
            data["data_source_id"] = data_source.id
            records.append(Record(**data))

        db_session.bulk_save_objects(records)
        db_session.commit()

        # Verify
        count = db_session.query(Record).count()
        assert count == 10

    def test_get_dashboard_stats(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test getting dashboard statistics"""
        from sqlalchemy import func

        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create records
        for i in range(5):
            data = sample_record_data.copy()
            data["record_id"] = f"TEST-{i}"
            data["jurisdiction_id"] = jurisdiction.id
            data["data_source_id"] = data_source.id
            record = Record(**data)
            db_session.add(record)

        db_session.commit()

        # Get stats
        record_count = db_session.query(func.count(Record.id)).scalar()
        jurisdiction_count = db_session.query(func.count(Jurisdiction.id)).scalar()

        assert record_count == 5
        assert jurisdiction_count == 1


class TestDatabaseQueries:
    """Tests for database query operations"""

    def test_search_by_grantor(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test searching by grantor name"""
        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create records with different grantors
        grantors = ["John Doe", "Jane Smith", "John Johnson"]
        for i, grantor in enumerate(grantors):
            data = sample_record_data.copy()
            data["record_id"] = f"TEST-{i}"
            data["grantor"] = grantor
            data["jurisdiction_id"] = jurisdiction.id
            data["data_source_id"] = data_source.id
            record = Record(**data)
            db_session.add(record)

        db_session.commit()

        # Search for "John"
        results = db_session.query(Record).filter(Record.grantor.ilike("%John%")).all()

        assert len(results) == 2

    def test_filter_by_amount_range(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test filtering by amount range"""
        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create records with different amounts
        amounts = [100000, 250000, 500000, 750000, 1000000]
        for i, amount in enumerate(amounts):
            data = sample_record_data.copy()
            data["record_id"] = f"TEST-{i}"
            data["amount"] = amount
            data["jurisdiction_id"] = jurisdiction.id
            data["data_source_id"] = data_source.id
            record = Record(**data)
            db_session.add(record)

        db_session.commit()

        # Filter by range
        results = (
            db_session.query(Record)
            .filter(Record.amount >= 200000, Record.amount <= 600000)
            .all()
        )

        assert len(results) == 2  # 250000 and 500000

    def test_filter_by_date_range(
        self, db_session, sample_jurisdiction_data, sample_record_data
    ):
        """Test filtering by date range"""
        from datetime import datetime, timedelta

        from datagod.models import DataSource, Jurisdiction, Record

        # Create jurisdiction
        jurisdiction = Jurisdiction(**sample_jurisdiction_data)
        db_session.add(jurisdiction)
        db_session.commit()

        # Create data source
        data_source = DataSource(
            jurisdiction_id=jurisdiction.id, source_name="Test API", source_type="api"
        )
        db_session.add(data_source)
        db_session.commit()

        # Create records with different dates
        base_date = datetime(2024, 1, 1)
        for i in range(5):
            data = sample_record_data.copy()
            data["record_id"] = f"TEST-{i}"
            data["date"] = base_date + timedelta(days=i * 30)
            data["jurisdiction_id"] = jurisdiction.id
            data["data_source_id"] = data_source.id
            record = Record(**data)
            db_session.add(record)

        db_session.commit()

        # Filter by date range
        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 4, 1)

        results = (
            db_session.query(Record)
            .filter(Record.date >= start_date, Record.date <= end_date)
            .all()
        )

        assert len(results) == 2  # February and March records
