
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def init_db():
    try:
        # Connect to default postgres database to create user and new db
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='datagod'")
        if not cur.fetchone():
            print("Creating user 'datagod'...")
            cur.execute("CREATE USER datagod WITH PASSWORD 'datagod';")
            cur.execute("ALTER USER datagod CREATEDB;")
        else:
            print("User 'datagod' already exists. Updating password...")
            cur.execute("ALTER USER datagod WITH PASSWORD 'datagod';")
            
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname='datagod'")
        if not cur.fetchone():
            print("Creating database 'datagod'...")
            cur.execute("CREATE DATABASE datagod OWNER datagod;")
        else:
            print("Database 'datagod' already exists.")
            
        # Grant privileges
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE datagod TO datagod;")
        
        conn.close()
        print("Database initialization complete.")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
