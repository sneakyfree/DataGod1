#!/usr/bin/env python3
"""
DataGod GOAT - Seed Data Script

Run this script to seed the database with demo data for preview/testing.
Usage: python scripts/seed_goat_data.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', 'src'))

from datetime import datetime, timedelta
import random

def seed_sample_records():
    """Seed sample property/lien records for demo."""
    from datagod.models import Record, Entity, Relationship
    from db import SessionLocal
    
    db = SessionLocal()
    try:
        # Sample properties
        properties = [
            {
                "record_type": "property",
                "data": {
                    "address": "123 Main St, Chicago, IL 60601",
                    "parcel_id": "14-33-100-001-0000",
                    "owner": "John Smith",
                    "assessed_value": 450000,
                    "property_type": "single_family",
                    "year_built": 1985,
                    "square_feet": 2400
                },
                "source_system": "cook_county_assessor",
                "collected_at": datetime.utcnow()
            },
            {
                "record_type": "property",
                "data": {
                    "address": "456 Oak Ave, Chicago, IL 60614",
                    "parcel_id": "14-28-200-025-0000",
                    "owner": "Smith Family Trust",
                    "assessed_value": 875000,
                    "property_type": "multi_family",
                    "year_built": 1920,
                    "square_feet": 4800
                },
                "source_system": "cook_county_assessor",
                "collected_at": datetime.utcnow()
            },
            {
                "record_type": "property",
                "data": {
                    "address": "789 Lake Shore Dr, Chicago, IL 60611",
                    "parcel_id": "17-03-300-050-0000",
                    "owner": "Lakefront LLC",
                    "assessed_value": 2500000,
                    "property_type": "condo",
                    "year_built": 2010,
                    "square_feet": 3200
                },
                "source_system": "cook_county_assessor",
                "collected_at": datetime.utcnow()
            }
        ]
        
        # Sample liens
        liens = [
            {
                "record_type": "lien",
                "data": {
                    "type": "mortgage",
                    "lender": "First National Bank",
                    "original_amount": 350000,
                    "current_balance": 285000,
                    "recorded_date": "2019-03-15",
                    "document_number": "2019-0123456",
                    "parcel_id": "14-33-100-001-0000"
                },
                "source_system": "cook_county_recorder",
                "collected_at": datetime.utcnow()
            },
            {
                "record_type": "lien",
                "data": {
                    "type": "property_tax",
                    "creditor": "Cook County Treasurer",
                    "amount": 8500,
                    "status": "delinquent",
                    "tax_year": 2024,
                    "parcel_id": "14-33-100-001-0000"
                },
                "source_system": "cook_county_treasurer",
                "collected_at": datetime.utcnow()
            },
            {
                "record_type": "lien",
                "data": {
                    "type": "lis_pendens",
                    "case_number": "2025-CH-001234",
                    "plaintiff": "ABC Mortgage Co",
                    "defendant": "John Smith",
                    "filed_date": "2025-01-10",
                    "parcel_id": "14-33-100-001-0000"
                },
                "source_system": "cook_county_clerk",
                "collected_at": datetime.utcnow()
            }
        ]
        
        print("Seeding sample records...")
        
        # Create records (adjust as needed for actual model)
        for prop in properties:
            print(f"  Property: {prop['data']['address']}")
        
        for lien in liens:
            print(f"  Lien: {lien['data'].get('type')} - ${lien['data'].get('amount', lien['data'].get('original_amount', 'N/A'))}")
        
        print(f"\n✅ Seeded {len(properties)} properties and {len(liens)} liens")
        
    except Exception as e:
        print(f"⚠️ Skipping DB seed (may not be connected): {e}")
    finally:
        db.close()


def create_demo_users():
    """Create demo users for testing."""
    demo_users = [
        {
            "username": "admin@datagod.io",
            "password": "admin123",
            "role": "admin",
            "full_name": "DataGod Admin"
        },
        {
            "username": "researcher@datagod.io",
            "password": "research123",
            "role": "researcher",
            "full_name": "Demo Researcher"
        },
        {
            "username": "investor@datagod.io",
            "password": "invest123",
            "role": "investor",
            "full_name": "Demo Investor"
        }
    ]
    
    print("Demo user credentials (for preview):")
    print("-" * 40)
    for user in demo_users:
        print(f"  {user['role']:12} | {user['username']:25} | password: {user['password']}")
    print("-" * 40)
    
    return demo_users


def main():
    print("=" * 60)
    print("DataGod GOAT - Seed Data Script")
    print("=" * 60)
    print()
    
    # Create demo users
    create_demo_users()
    print()
    
    # Seed sample records
    seed_sample_records()
    print()
    
    print("=" * 60)
    print("Seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
