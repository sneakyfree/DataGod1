#!/usr/bin/env python3
"""
Create quick login accounts for development/testing.
Run this script to seed the database with test accounts.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from db_manager import DatabaseManager

# Password hashing context (same as used in API)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


# Define quick login accounts
QUICK_LOGIN_ACCOUNTS = [
    {
        "username": "superadmin",
        "email": "superadmin@datagod.local",
        "password": "superadmin123",
        "full_name": "Super Administrator",
        "roles": ["superadmin", "admin", "user"],
        "subscription_tier": "enterprise",
        "email_verified": True,
    },
    {
        "username": "admin",
        "email": "admin@datagod.local",
        "password": "admin123",
        "full_name": "Administrator",
        "roles": ["admin", "user"],
        "subscription_tier": "pro",
        "email_verified": True,
    },
    {
        "username": "user",
        "email": "user@datagod.local",
        "password": "user123",
        "full_name": "Regular User",
        "roles": ["user"],
        "subscription_tier": "free",
        "email_verified": True,
    },
    {
        "username": "salesrep",
        "email": "salesrep@datagod.local",
        "password": "sales123",
        "full_name": "Sales Representative",
        "roles": ["sales", "user"],
        "subscription_tier": "pro",
        "email_verified": True,
    },
]


def create_accounts():
    """Create all quick login accounts."""
    print("Creating quick login accounts...")
    print("-" * 50)

    # Initialize database manager
    db = DatabaseManager()

    # Ensure database tables exist
    db.init_database()

    created_count = 0

    for account in QUICK_LOGIN_ACCOUNTS:
        username = account["username"]

        # Check if user already exists
        existing = db.get_user_by_username(username)
        if existing:
            print(f"  [SKIP] {username} - already exists")
            continue

        # Hash the password
        hashed_password = get_password_hash(account["password"])

        # Create the user
        user_id = db.create_user(
            username=username,
            email=account["email"],
            hashed_password=hashed_password,
            full_name=account["full_name"],
            roles=account["roles"],
            disabled=False,
            email_verified=account["email_verified"],
            subscription_tier=account["subscription_tier"],
        )

        if user_id:
            print(f"  [OK] Created {username} (ID: {user_id})")
            created_count += 1
        else:
            print(f"  [ERROR] Failed to create {username}")

    print("-" * 50)
    print(f"Created {created_count} new accounts")
    print()
    print("Quick Login Credentials:")
    print("=" * 50)
    for account in QUICK_LOGIN_ACCOUNTS:
        print(f"  {account['full_name']}:")
        print(f"    Username: {account['username']}")
        print(f"    Password: {account['password']}")
        print(f"    Roles: {', '.join(account['roles'])}")
        print()


if __name__ == "__main__":
    create_accounts()
