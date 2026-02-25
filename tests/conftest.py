import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_conn

def _init_schema(conn: sqlite3.Connection) -> None:
    """
        To prevent contamination of the original database, a separate test database should be established.
    """
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS postcode_map;
        DROP TABLE IF EXISTS areas;

        CREATE TABLE areas (
            area_code TEXT PRIMARY KEY,
            area_name TEXT NOT NULL
        );

        CREATE TABLE postcode_map (
            postcode   TEXT PRIMARY KEY,
            area_code  TEXT NOT NULL,
            FOREIGN KEY (area_code) REFERENCES areas(area_code)
        );
        """
    )
    conn.commit()

def _seed_data(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO areas(area_code, area_name) VALUES (?, ?)",
        [
            ("E08000035", "Leeds"),
            ("E08000025", "Birmingham"),
            ("E07000240", "St Albans"),
        ],
    )
    conn.executemany(
        "INSERT INTO postcode_map(postcode, area_code) VALUES (?, ?)",
        [
            ("LS11AA", "E08000035"),
            ("LS29JT", "E08000035"),
            ("B11AA", "E08000025"),
        ],
    )
    conn.commit()

@pytest.fixture()
def db_conn(tmp_path):
    """
        Each test function uses a completely new database,
        and they do not affect each other.
    """
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    _init_schema(conn)
    _seed_data(conn)

    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture()
def client(db_conn):
    """
    Override the get_conn dependency to allow the API to use the test database.
    """
    def _override_get_conn():
        try:
            yield db_conn
        finally:
            pass

    app.dependency_overrides[get_conn] = _override_get_conn

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()