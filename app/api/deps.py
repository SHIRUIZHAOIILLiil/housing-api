import sqlite3
from typing import Generator
from app.core.config import Settings

settings = Settings()

def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


