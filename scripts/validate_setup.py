#!/usr/bin/env python3
"""
DataGod Setup Validation Script

This script validates that the DataGod platform is correctly set up:
1. Database connection works
2. Models are properly configured
3. db_manager operations work
4. API configuration is valid
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, passed: bool, message: str = ""):
    """Print test result."""
    status = "PASS" if passed else "FAIL"
    icon = "[OK]" if passed else "[X]"
    print(f"  {icon} {test_name}: {status}")
    if message:
        print(f"      {message}")


def test_imports():
    """Test that all required modules can be imported."""
    print_header("Testing Imports")

    tests = [
        ("datagod.config.settings", None),
        ("datagod.models", None),
        ("db_manager", None),
    ]

    all_passed = True
    for module_name, expected_attr in tests:
        try:
            module = __import__(module_name, fromlist=[''])
            if expected_attr:
                getattr(module, expected_attr)
            print_result(f"Import {module_name}", True)
        except Exception as e:
            print_result(f"Import {module_name}", False, str(e))
            all_passed = False

    return all_passed


def test_database_connection():
    """Test database connectivity."""
    print_header("Testing Database Connection")

    try:
        from db_manager import DatabaseManager
        db = DatabaseManager()
        print_result("DatabaseManager instantiation", True)
    except Exception as e:
        print_result("DatabaseManager instantiation", False, str(e))
        return False

    try:
        result = db.init_database()
        print_result("Database initialization", result)
    except Exception as e:
        print_result("Database initialization", False, str(e))
        return False

    return True


def test_crud_operations():
    """Test basic CRUD operations."""
    print_header("Testing CRUD Operations")

    from db_manager import DatabaseManager
    db = DatabaseManager()

    all_passed = True

    # Test Jurisdiction CRUD
    try:
        jid = db.create_jurisdiction(
            name=f"Test County {datetime.now().timestamp()}",
            state="TX",
            jurisdiction_type="county",
            description="Test jurisdiction for validation"
        )
        print_result("Create Jurisdiction", jid is not None, f"ID: {jid}")

        if jid:
            jurisdiction = db.get_jurisdiction(jid)
            print_result("Read Jurisdiction", jurisdiction is not None)

            update_result = db.update_jurisdiction(jid, population=100000)
            print_result("Update Jurisdiction", update_result)

            delete_result = db.delete_jurisdiction(jid)
            print_result("Delete Jurisdiction", delete_result)
    except Exception as e:
        print_result("Jurisdiction CRUD", False, str(e))
        all_passed = False

    # Test Entity CRUD
    try:
        eid = db.create_entity(
            entity_name="Test Person",
            entity_type="person",
            city="Houston",
            state="TX"
        )
        print_result("Create Entity", eid is not None, f"ID: {eid}")

        if eid:
            entity = db.get_entity(eid)
            print_result("Read Entity", entity is not None)
    except Exception as e:
        print_result("Entity CRUD", False, str(e))
        all_passed = False

    return all_passed


def test_search_operations():
    """Test search operations."""
    print_header("Testing Search Operations")

    from db_manager import DatabaseManager
    db = DatabaseManager()

    all_passed = True

    try:
        # List jurisdictions
        jurisdictions = db.list_jurisdictions(limit=5)
        print_result("List Jurisdictions", True, f"Found {len(jurisdictions)} jurisdictions")

        # Search entities
        entities = db.search_entities(limit=5)
        print_result("Search Entities", True, f"Found {len(entities)} entities")

        # Search records
        records = db.search_records(limit=5)
        print_result("Search Records", True, f"Found {len(records)} records")

    except Exception as e:
        print_result("Search Operations", False, str(e))
        all_passed = False

    return all_passed


def test_dashboard_stats():
    """Test dashboard statistics."""
    print_header("Testing Dashboard Statistics")

    from db_manager import DatabaseManager
    db = DatabaseManager()

    try:
        stats = db.get_dashboard_stats()
        print_result("Get Dashboard Stats", True)
        print(f"\n  Current Database Statistics:")
        print(f"    - Total Records: {stats['totalRecords']}")
        print(f"    - Jurisdictions: {stats['jurisdictions']}")
        print(f"    - Data Sources: {stats['dataSources']}")
        print(f"    - Active Scrapers: {stats['activeScrapers']}")
        print(f"    - Total Entities: {stats['totalEntities']}")
        return True
    except Exception as e:
        print_result("Get Dashboard Stats", False, str(e))
        return False


def test_api_config():
    """Test API configuration."""
    print_header("Testing API Configuration")

    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'api', 'src'
        ))
        from config import settings
        print_result("Load API Settings", True)
        print(f"\n  API Configuration:")
        print(f"    - API Title: {settings.api_title}")
        print(f"    - API Version: {settings.api_version}")
        print(f"    - Database URL: {settings.database_url[:30]}...")
        return True
    except Exception as e:
        print_result("Load API Settings", False, str(e))
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("       DataGod Setup Validation")
    print("=" * 60)
    print(f"  Timestamp: {datetime.now().isoformat()}")

    results = {
        "imports": test_imports(),
        "database": test_database_connection(),
        "crud": test_crud_operations(),
        "search": test_search_operations(),
        "stats": test_dashboard_stats(),
        "api_config": test_api_config()
    }

    # Summary
    print_header("Validation Summary")
    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  [SUCCESS] All validation tests passed!")
        print("  DataGod is ready to use.")
        print("\n  Next steps:")
        print("    1. Run: python cli.py seed")
        print("    2. Run: python cli.py serve --reload")
        print("    3. Open: http://localhost:8000/docs")
        return 0
    else:
        print(f"\n  [WARNING] {total - passed} test(s) failed.")
        print("  Please check the errors above and fix them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
