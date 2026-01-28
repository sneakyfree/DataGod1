
import psycopg2
import sys

def test_connection(password):
    try:
        conn = psycopg2.connect(
            dbname="datagod",
            user="datagod",
            password=password,
            host="localhost",
            port="5432"
        )
        conn.close()
        print(f"SUCCESS: Connected with password '{password}'")
        return True
    except psycopg2.OperationalError as e:
        print(f"FAILED: Password '{password}' failed. Error: {e}")
        return False

users = ["datagod", "postgres", "admin", "root"]
passwords = [
    "datagod", "datagod_secure_password", "datagod_dev_password",
    "postgres", "password", "admin", "root", "secret", "123456", ""
]
success = False

for user in users:
    for pwd in passwords:
        try:
            conn = psycopg2.connect(
                dbname="datagod", # Try connecting to datagod db
                user=user,
                password=pwd,
                host="localhost",
                port="5432"
            )
            conn.close()
            print(f"SUCCESS: Connected with User: '{user}', Password: '{pwd}' to 'datagod'")
            success = True
            break
        except psycopg2.OperationalError as e:
            if "database" in str(e) and "does not exist" in str(e):
                 # User might be right but DB wrong. Try connecting to default 'postgres' db
                try:
                    conn = psycopg2.connect(
                        dbname="postgres",
                        user=user,
                        password=pwd,
                        host="localhost",
                        port="5432"
                    )
                    conn.close()
                    print(f"SUCCESS: Connected with User: '{user}', Password: '{pwd}' to 'postgres'")
                    success = True
                    break
                except Exception:
                    pass
            pass
    if success:
        break

if not success:
    sys.exit(1)
