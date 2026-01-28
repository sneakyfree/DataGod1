
import psycopg2
from psycopg2 import sql

def check_db_state():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check users
        cur.execute("SELECT usename FROM pg_user;")
        users = [r[0] for r in cur.fetchall()]
        print(f"Users: {users}")
        
        # Check databases
        cur.execute("SELECT datname FROM pg_database;")
        dbs = [r[0] for r in cur.fetchall()]
        print(f"Databases: {dbs}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

check_db_state()
