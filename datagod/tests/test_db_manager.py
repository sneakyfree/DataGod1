# datagod/tests/test_db_manager.py
"""
Tests for datagod.db_manager module - uses string parameters, not models
"""
import os
import tempfile
import unittest

from datagod.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager with string-based API"""

    def setUp(self):
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)

    def tearDown(self):
        # Clean up the temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_create_jurisdiction(self):
        """Test creating a jurisdiction using string parameters"""
        # The actual API takes strings, not model objects
        jurisdiction_id = self.db_manager.create_jurisdiction(
            name="Test Jurisdiction", state="Test State", country="Test Country"
        )
        self.assertIsInstance(jurisdiction_id, int)
        self.assertGreater(jurisdiction_id, 0)

    def test_get_jurisdiction(self):
        """Test getting a jurisdiction by ID"""
        jurisdiction_id = self.db_manager.create_jurisdiction(
            name="Test Jurisdiction Get", state="Test State", country="Test Country"
        )

        retrieved_jurisdiction = self.db_manager.get_jurisdiction(jurisdiction_id)

        self.assertIsNotNone(retrieved_jurisdiction)
        # Returns a dict or Row object
        self.assertEqual(retrieved_jurisdiction["name"], "Test Jurisdiction Get")
        self.assertEqual(retrieved_jurisdiction["state"], "Test State")
        self.assertEqual(retrieved_jurisdiction["country"], "Test Country")

    def test_create_data_source(self):
        """Test creating a data source using string parameters"""
        data_source_id = self.db_manager.create_data_source(
            name="Test Data Source",
            url="http://example.com",
            description="Test description",
        )
        self.assertIsInstance(data_source_id, int)
        self.assertGreater(data_source_id, 0)

    def test_create_record(self):
        """Test creating a record"""
        # First create jurisdiction and data source
        jurisdiction_id = self.db_manager.create_jurisdiction(
            name="Test Jurisdiction Record", state="Test State", country="Test Country"
        )

        data_source_id = self.db_manager.create_data_source(
            name="Test Data Source Record",
            url="http://example.com",
            description="Test description",
        )

        # Create record using string parameters
        record_id = self.db_manager.create_record(
            jurisdiction_id=jurisdiction_id,
            data_source_id=data_source_id,
            title="Test Record",
            description="Test description",
            amount=1000.0,
            date="2023-01-01",
            url="http://example.com/record",
        )
        self.assertIsInstance(record_id, int)
        self.assertGreater(record_id, 0)

    def test_search_records(self):
        """Test searching records"""
        # The DatabaseManager methods don't commit transactions except for jurisdictions
        # So we need to use raw SQL with explicit commit for data_source and record creation

        with self.db_manager.get_connection() as conn:
            # Create jurisdiction
            conn.execute(
                """
                INSERT INTO jurisdictions (name, state, country)
                VALUES (?, ?, ?)
            """,
                ("Test Jurisdiction Search", "Test State", "Test Country"),
            )

            # Create data source
            conn.execute(
                """
                INSERT INTO data_sources (name, url, description)
                VALUES (?, ?, ?)
            """,
                ("Test Data Source Search", "http://example.com", "Test description"),
            )

            # Get the IDs
            cursor = conn.execute(
                "SELECT id FROM jurisdictions WHERE name = ?",
                ("Test Jurisdiction Search",),
            )
            jurisdiction_id = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT id FROM data_sources WHERE name = ?",
                ("Test Data Source Search",),
            )
            data_source_id = cursor.fetchone()[0]

            # Create records
            conn.execute(
                """
                INSERT INTO records (jurisdiction_id, data_source_id, title, description, amount, date, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    jurisdiction_id,
                    data_source_id,
                    "Searchable Record One",
                    "Test description one",
                    1000.0,
                    "2023-01-01",
                    "http://example.com/record1",
                ),
            )

            conn.execute(
                """
                INSERT INTO records (jurisdiction_id, data_source_id, title, description, amount, date, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    jurisdiction_id,
                    data_source_id,
                    "Searchable Record Two",
                    "Another test description",
                    2000.0,
                    "2023-01-02",
                    "http://example.com/record2",
                ),
            )

            conn.commit()

        # Search for records - should find both
        results = self.db_manager.search_records("Searchable")
        self.assertEqual(len(results), 2)

        # Search by description
        results = self.db_manager.search_records("description")
        self.assertGreaterEqual(len(results), 2)

        # Search for non-existent
        results = self.db_manager.search_records("totally_nonexistent_xyz123")
        self.assertEqual(len(results), 0)

    def test_create_duplicate_jurisdiction(self):
        """Test creating duplicate jurisdiction returns existing ID"""
        jurisdiction_id1 = self.db_manager.create_jurisdiction(
            name="Duplicate Test", state="TX", country="USA"
        )

        # Creating same jurisdiction should return the existing ID
        jurisdiction_id2 = self.db_manager.create_jurisdiction(
            name="Duplicate Test", state="TX", country="USA"
        )

        self.assertEqual(jurisdiction_id1, jurisdiction_id2)

    def test_connection_context_manager(self):
        """Test database connection context manager"""
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
            # Should be able to execute queries
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)


if __name__ == "__main__":
    unittest.main()
