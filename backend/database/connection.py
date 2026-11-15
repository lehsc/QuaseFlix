import psycopg
from contextlib import contextmanager

DATABASE_URL = "postgresql://postgres:quaseflix@localhost:5432/quaseflix"

@contextmanager
def get_db_connection():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()   
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()