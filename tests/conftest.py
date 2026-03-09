import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
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
        DROP TABLE IF EXISTS rent_stats_official;
        DROP TABLE IF EXISTS sales_transactions_official;
        DROP TABLE IF EXISTS sales_transactions_user;
        DROP TABLE IF EXISTS rent_stats_user;
        DROP TABLE IF EXISTS audit_logs;
        DROP TABLE IF EXISTS users;
        
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE audit_logs (
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

        CREATE TABLE areas (
            area_code TEXT PRIMARY KEY,
            area_name TEXT NOT NULL
        );

        CREATE TABLE postcode_map (
            postcode   TEXT PRIMARY KEY,
            area_code  TEXT NOT NULL,
            FOREIGN KEY (area_code) REFERENCES areas(area_code)
        );
        
        CREATE TABLE rent_stats_official (
            time_period TEXT NOT NULL,
            area_code TEXT NOT NULL,
            region_or_country_name TEXT NOT NULL,
            index_value REAL,
            annual_change REAL,
            rental_price REAL,
            index_one_bed REAL,
            rental_price_one_bed REAL,
            index_two_bed REAL,
            rental_price_two_bed REAL,
            index_three_bed REAL,
            rental_price_three_bed REAL,
            rental_price_detached REAL,
            rental_price_semidetached REAL,
            rental_price_terraced REAL,
            rental_price_flat_maisonette REAL,
            PRIMARY KEY(time_period, area_code)
            );
            
        CREATE TABLE sales_transactions_official (
                transaction_uuid TEXT PRIMARY KEY,
                price REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                postcode TEXT, 
                property_type TEXT CHECK ( property_type IS NULL OR property_type IN ( 'F', 'D', 'S', 'T', 'O')),
                new_build INTEGER CHECK ( new_build IS NULL OR new_build IN ( 0, 1 )),
                tenure TEXT CHECK (tenure IS NULL OR tenure IN ('L', 'F')),
                paon TEXT,
                saon TEXT,
                FOREIGN KEY( postcode) REFERENCES postcode_map (postcode)
        );
        
        CREATE TABLE IF NOT EXISTS rent_stats_user(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                postcode TEXT, 
                area_code TEXT,
                time_period TEXT NOT NULL,
                rent REAL NOT NULL,
                bedrooms INTEGER,
                property_type TEXT,
                created_at TEXT,
                source TEXT DEFAULT 'user' CHECK ( source IN ('user', 'survey', 'partner')),
                uploader_id INTEGER,
                FOREIGN KEY (postcode)REFERENCES postcode_map( postcode),
                FOREIGN KEY (area_code) REFERENCES areas(area_code)
                );
                
        CREATE TABLE IF NOT EXISTS sales_transactions_user(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                postcode TEXT,
                area_code TEXT,
                time_period TEXT NOT NULL,
                price REAL NOT NULL,
                property_type TEXT,
                created_at TEXT,
                source TEXT DEFAULT 'user' CHECK ( source IN ('user', 'survey', 'partner')),
                uploader_id INTEGER,
                FOREIGN KEY (postcode)REFERENCES postcode_map( postcode),
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
            ("E08000003", "Manchester"),
            ("E09000033", "Westminster"),
            ("E09000025", "Newham"),
        ],
    )
    conn.executemany(
        "INSERT INTO postcode_map(postcode, area_code) VALUES (?, ?)",
        [
            ("LS29JT", "E08000035"),
            ("LS81NX", "E08000035"),
            ("LS73PE", "E08000035"),

            ("AL13BH", "E07000240"),
            ("AL13UE", "E07000240"),
            ("AL40DL", "E07000240"),
            ("LS11AA", "E08000035"),
            ("LS28JT", "E08000035"),
            ('LS62UW', 'E08000035'),
            ('LS81BY', 'E08000035'),
            ('M12AB', 'E08000003'),
            ('M146PL', 'E08000003'),
            ('SW1A1AA', 'E09000033'),
            ('SW113DL', 'E09000033'),
            ('B11AA', 'E08000025'),
            ('B152TT', 'E08000025'),

            ('LS12AB', 'E08000035'),
            ('LS63EF', 'E08000035'),
            ('LS84GH', 'E08000035'),

            ('M13AA', 'E08000003'),
            ('M202WX', 'E08000003'),

            ('B236XY', 'E08000025'),

            ('W1D4EG', 'E09000033'),


        ],
    )

    conn.executemany(
        "INSERT INTO rent_stats_official(time_period, area_code, region_or_country_name, "
        "index_value, annual_change, rental_price, index_one_bed, "
        "rental_price_one_bed, index_two_bed, rental_price_two_bed, "
        "index_three_bed, rental_price_three_bed, rental_price_detached, "
        "rental_price_semidetached, rental_price_terraced, rental_price_flat_maisonette) "
        "                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("2017-02", "E08000035", "Yorkshire and The Humber", 76.301508, 2.97153, 755, 77.04281, 509, 77.510328, 645,
             76.097967, 739, 1009, 805, 759, 602),
            ("2017-03", "E08000035", "Yorkshire and The Humber", 76.60377, 3.465849, 758, 77.351031, 511, 77.778606,
             647, 76.434108, 742, 1012, 808, 763, 604),
            ("2017-04", "E08000035", "Yorkshire and The Humber", 77.461433, 4.295108, 767, 78.267663, 517, 78.638306,
             655, 77.30701, 751, 1023, 817, 771, 611),
            ("2017-05", "E08000035", "Yorkshire and The Humber", 78.287746, 4.798483, 775, 79.152734, 523, 79.467563,
             661, 78.104831, 759, 1035, 826, 779, 617),
            ("2017-06", "E08000035", "Yorkshire and The Humber", 78.770196, 5.226974, 780, 79.698707, 527, 79.964345,
             666, 78.549998, 763, 1041, 831, 784, 622),
            ("2017-02", "E08000025", "West Midlands", 85.628118, 3.820591, 732, 86.258115, 551, 87.016289, 677,
             85.353832, 749, 985, 762, 720, 619),
            ("2017-03", "E08000025", "West Midlands", 85.368076, 3.259523, 730, 85.95749, 549, 86.664787, 675,
             85.108751, 747, 982, 760, 718, 616),
            ("2017-04", "E08000025", "West Midlands", 85.134765, 2.763049, 728, 85.753101, 547, 86.391956, 673,
             84.847053, 744, 979, 758, 716, 615),
            ("2017-05", "E08000025", "West Midlands", 85.221691, 2.73176, 729, 85.912716, 549, 86.491647, 673,
             84.917283, 745, 980, 758, 717, 615),
            ("2017-06", "E08000025", "West Midlands", 85.694207, 3.147173, 733, 86.494904, 552, 87.037466, 678,
             85.380413, 749, 985, 762, 720, 619),
            ("2017-02", "E07000240", "East of England", 83.746338, 4.106414, 1334, 83.872284, 863, 84.645042, 1130,
             83.417845, 1383, 1889, 1485, 1231, 1025),
            ("2017-03", "E07000240", "East of England", 84.020129, 4.572975, 1338, 84.16037, 866, 84.886778, 1133,
             83.713821, 1388, 1894, 1490, 1235, 1029),
            ("2017-04", "E07000240", "East of England", 84.218779, 4.551375, 1342, 84.406039, 868, 85.077614, 1135,
             83.905043, 1391, 1899, 1494, 1238, 1031),
            ("2017-05", "E07000240", "East of England", 84.377381, 4.335114, 1344, 84.613663, 870, 85.232459, 1137,
             84.053672, 1394, 1903, 1497, 1240, 1033),
            ("2017-06", "E07000240", "East of England", 84.536721, 3.911254, 1347, 84.846948, 873, 85.417459, 1140,
             84.200212, 1396, 1906, 1499, 1242, 1036),
        ],
    )

    conn.executemany(
        "INSERT INTO sales_transactions_official (transaction_uuid, price, transaction_date, "
        "postcode, property_type, new_build, tenure, paon, saon) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("b0a9d11b-f029-4c1f-e053-6c04a8c0d716", 427500, "2020-08-03", "LS81NX", "S", 0, "F", "66", None),
            ("b0a9d11b-f10d-4c1f-e053-6c04a8c0d716", 153500, "2020-08-21", "LS73PE", "T", 0, "F", "5", None),
            ("a2479555-5142-74c7-e053-6b04a8c0887d", 295000, "2020-02-14", "AL13UE", "F", 1, "L", "ZIGGURAT HOUSE 25", "FLAT 39"),
            ("a2479555-505d-74c7-e053-6b04a8c0887d", 220000, "2020-01-31", "AL40DL", "F", 0, "L", "17","FLAT 1")
        ],
    )

    conn.executemany(
        "INSERT INTO rent_stats_user (postcode, area_code, time_period, rent, bedrooms, property_type, created_at, source, uploader_id)"
        " VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ('LS11AA', 'E08000035', '2024-06', 850, 1, 'flat', '2025-02-20 10:00:00', 'user', 1),
            ('LS28JT', 'E08000035', '2024-06', 1150, 2, 'flat', '2025-02-20 10:05:00', 'user', 1),
            ('LS62UW', 'E08000035', '2024-07', 1350, 3, 'terraced', '2025-02-20 10:10:00', 'user', 1),
            ('LS81BY', 'E08000035', '2024-07', 1600, 4, 'semidetached', '2025-02-20 10:12:00', 'user', 1),
            ('M12AB', 'E08000003', '2024-06', 900, 1, 'flat', '2025-02-20 11:00:00', 'user', 1),
            ('M146PL', 'E08000003', '2024-07', 1400, 3, 'terraced', '2025-02-20 11:05:00', 'user', 1),
            ('SW1A1AA', 'E09000033', '2024-06', 2100, 2, 'flat', '2025-02-20 11:10:00', 'user', 1),
            ('SW113DL', 'E09000033', '2024-07', 2800, 3, 'detached', '2025-02-20 11:12:00', 'user', 1),
            ('B11AA', 'E08000025', '2024-06', 800, 1, 'flat', '2025-02-20 11:20:00', 'user', 1),
            ('B152TT', 'E08000025', '2024-07', 1250, 3, 'semidetached', '2025-02-20 11:25:00', 'user', 1)
        ],
    )

    conn.executemany(
        "INSERT INTO sales_transactions_user (postcode, area_code, time_period, price, property_type, created_at, source, uploader_id) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ('LS12AB', 'E08000035', '2024-06', 225000, 'flat', '2025-02-21 18:00:00', 'user', 1),
            ('LS63EF', 'E08000035', '2024-07', 310000, 'terraced', '2025-02-21 18:05:00', 'user', 1),
            ('LS84GH', 'E08000035', '2024-08', 345000, 'semidetached', '2025-02-21 18:10:00', 'user', 1),

            ('M13AA', 'E08000003', '2024-06', 260000, 'flat', '2025-02-21 18:15:00', 'user', 1),
            ('M146PL', 'E08000003', '2024-07', 385000, 'detached', '2025-02-21 18:20:00', 'user', 1),
            ('M202WX', 'E08000003', '2024-08', 295000, 'terraced', '2025-02-21 18:25:00', 'user', 1),

            ('B11AA', 'E08000025', '2024-06', 195000, 'flat', '2025-02-21 18:30:00', 'user', 1),
            ('B152TT', 'E08000025', '2024-07', 275000, 'semidetached', '2025-02-21 18:35:00', 'user', 1),
            ('B236XY', 'E08000025', '2024-08', 315000, 'detached', '2025-02-21 18:40:00', 'user', 1),

            ('SW1A1AA', 'E09000033', '2024-06', 720000, 'flat', '2025-02-21 18:45:00', 'user', 1),
            ('SW113DL', 'E09000033', '2024-07', 980000, 'semidetached', '2025-02-21 18:50:00', 'user', 1),
            ('W1D4EG', 'E09000033', '2024-08', 1250000, 'detached', '2025-02-21 18:55:00', 'user', 1)
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
    conn = sqlite3.connect(db_file, check_same_thread=False)
    _init_schema(conn)
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

    app = create_app()
    app.dependency_overrides[get_conn] = _override_get_conn

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture()
def registered_user(client):
    payload = {
        "username": "tester01",
        "email": "tester01@example.com",
        "password": "Test1234"
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return payload, r.json()


@pytest.fixture()
def auth_headers(client, registered_user):
    payload, _ = registered_user
    r = client.post(
        "/auth/login",
        data={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def second_user(client):
    payload = {
        "username": "tester02",
        "email": "tester02@example.com",
        "password": "Test2234"
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return payload, r.json()


@pytest.fixture()
def second_auth_headers(client, second_user):
    payload, _ = second_user
    r = client.post(
        "/auth/login",
        data={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def latest_audit_log(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row


def audit_logs_for(conn: sqlite3.Connection, action: str = None, resource_type: str = None):
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if action is not None:
        sql += " AND action = ?"
        params.append(action)
    if resource_type is not None:
        sql += " AND resource_type = ?"
        params.append(resource_type)

    sql += " ORDER BY id ASC"
    return conn.execute(sql, tuple(params)).fetchall()