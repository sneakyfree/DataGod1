#!/usr/bin/env python3
"""
Database Setup Script
Initializes the database and creates all tables
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datagod.config.settings import DATABASE_URL
from datagod.models import create_tables, reset_database, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Set up the database with all tables"""
    print("🚀 Setting up DataGod database...")
    print(f"📊 Database URL: {DATABASE_URL}")

    try:
        # Test database connection
        print("🔗 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")

        # Create all tables
        print("📋 Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully")

        # Verify tables exist
        print("🔍 Verifying table creation...")
        with engine.connect() as conn:
            if DATABASE_URL.startswith("sqlite"):
                # SQLite query
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                tables = [row[0] for row in result.fetchall()]
            else:
                # PostgreSQL query
                result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
                tables = [row[0] for row in result.fetchall()]

            expected_tables = ['jurisdictions', 'data_sources', 'records', 'entities', 'relationships']
            created_tables = [t for t in tables if t in expected_tables]

            print(f"📊 Found {len(created_tables)} DataGod tables:")
            for table in sorted(created_tables):
                print(f"   ✓ {table}")

            if len(created_tables) >= len(expected_tables):
                print("✅ All expected tables created successfully")
            else:
                missing = set(expected_tables) - set(created_tables)
                print(f"⚠️  Missing tables: {missing}")

        print("\n🎉 Database setup complete!")
        print("💡 Next steps:")
        print("   1. Run 'alembic revision --autogenerate -m \"Initial schema\"' to create migration")
        print("   2. Run 'alembic upgrade head' to apply migration")
        print("   3. Start developing your DataGod application!")

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def reset_database_interactive():
    """Reset the database with confirmation"""
    print("⚠️  WARNING: This will delete all data in the database!")
    response = input("Are you sure you want to reset the database? (yes/no): ").strip().lower()

    if response == 'yes':
        print("🔄 Resetting database...")
        reset_database()
        print("✅ Database reset complete")
        return True
    else:
        print("❌ Database reset cancelled")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database_interactive()
    else:
        setup_database()
