
import psycopg2

def check_tables():
    try:
        conn = psycopg2.connect(
            dbname="datagod_db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables in datagod_db: {tables}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking datagod_db: {e}")

check_tables()
