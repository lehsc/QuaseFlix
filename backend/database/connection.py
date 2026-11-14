import psycopg
from contextlib import contextmanager

DATABASE_URL = "postgresql://postgres:quaseflix@localhost:5432/quaseflix"

@contextmanager
def get_db_connection():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()  # Salva as alterações se tudo correr bem
    except Exception:
        conn.rollback()  # Desfaz em caso de erro
        raise
    finally:
        conn.close()