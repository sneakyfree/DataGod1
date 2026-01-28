
import os
# Ensure we load env vars if python-dotenv is not automatic (it usually is in app, but script might need help)
from dotenv import load_dotenv
load_dotenv()

from datagod.models import User
import sys
sys.path.append(os.getcwd())
from db_manager import DatabaseManager
from sqlalchemy.orm import Session

def verify():
    try:
        db = DatabaseManager()
        # Create a test session
        with db.get_session() as session:
            count = session.query(User).count()
            print(f"SUCCESS: Connected to DB. User count: {count}")
            
            # Create a test user if none exist
            if count == 0:
                print("Creating test user...")
                # Note: This relies on db_manager having explicit user creation methods or using session directly
                # db_manager.py seems to be generic, let's use session
                user = User(username="testadmin", email="admin@datagod.com", hashed_password="hashed_secret")
                session.add(user)
                session.commit()
                print("Test user created.")
                
        # Re-verify
        with db.get_session() as session:
            new_count = session.query(User).count()
            print(f"User count now: {new_count}")
            
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
