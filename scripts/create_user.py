import sqlite3
from app.core import Settings

def create_table_users(conn: sqlite3.Connection):
    sql_create_table_users = """
                            CREATE TABLE IF NOT EXISTS users
                            (
                                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                                username      TEXT NOT NULL UNIQUE,
                                email         TEXT NOT NULL UNIQUE,
                                password_hash TEXT NOT NULL,
                                created_at    TEXT NOT NULL );
                            """
    conn.execute(sql_create_table_users)
    conn.commit()


if __name__ == '__main__':
    settings = Settings()
    conn = sqlite3.connect(settings.DATABASE)
    create_table_users(conn)
    conn.close()