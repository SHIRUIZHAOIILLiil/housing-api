import sqlite3
from app.core import Settings

def create_table_logs(conn: sqlite3.Connection):
    sql_create_table_logs = """
                            CREATE TABLE IF NOT EXISTS audit_logs (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                action TEXT NOT NULL,
                                resource_type TEXT NOT NULL,
                                resource_id INTEGER,
                                request_id TEXT,
                                detail TEXT,
                                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (user_id) REFERENCES users(id)
                            );
                            """
    conn.execute(sql_create_table_logs)
    conn.commit()


if __name__ == '__main__':
    settings = Settings()
    conn = sqlite3.connect(settings.DATABASE)
    create_table_logs(conn)
    conn.close()