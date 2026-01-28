
import psycopg2
from datagod.config.settings import DATABASE_URL

def drop_all_tables():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cur.fetchall()
    
    if tables:
        print(f"Dropping {len(tables)} tables...")
        for table in tables:
            print(f"Dropping table {table[0]}...")
            cur.execute(f"DROP TABLE IF EXISTS \"{table[0]}\" CASCADE;")
    else:
        print("No tables found to drop.")
    
    conn.commit()
    conn.close()
    print("All tables dropped successfully.")

if __name__ == "__main__":
    drop_all_tables()
