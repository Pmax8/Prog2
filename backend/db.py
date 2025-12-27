import os
import mariadb


def get_db_connection():
    try:
        conn = mariadb.connect(
            host=os.getenv("DB_HOST", "mariadb"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "labuser"),
            password=os.getenv("DB_PASSWORD", "labpassword"),
            database=os.getenv("DB_NAME", "labdb"),
        )
        return conn
    except mariadb.Error as e:
        raise RuntimeError(f"Errore di connessione al database: {e}") from e