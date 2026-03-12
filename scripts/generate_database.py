import os
import sqlite3
import re
import pandas as pd
from app.core.config import Settings
from scripts import create_table_logs, create_table_users
column_name = ["transaction_uuid",
               "price",
               "transaction_date",
               "postcode",
               "property_type",
               "new_build",
               "tenure",
               "paon",
               "saon",
               "Street",
               "Locality",
               "Town/City",
               "District",
               "County",
               "PPD Category",
               "Record Status"]
column_name_pipr = [
    "Time period",
    "Area code",
    "Region or country name",
    "Index",
    "Annual change",
    "Rental price",
    "Index one bed",
    "Rental price one bed",
    "Index two bed",
    "Rental price two bed",
    "Index three bed",
    "Rental price three bed",
    "Rental price detached",
    "Rental price semidetached",
    "Rental price terraced",
    "Rental price flat maisonette", ]

numeric_cols = [
    "Index", "Annual change", "Rental price",
    "Index one bed", "Rental price one bed",
    "Index two bed", "Rental price two bed",
    "Index three bed", "Rental price three bed",
    "Rental price detached", "Rental price semidetached",
    "Rental price terraced", "Rental price flat maisonette",
]


def norm_postcode(x):
    if pd.isna(x):
        return None
    return re.sub(r"\s+", "", str(x).strip().upper())


def file_loader(settings: Settings):
    filepath = []
    base_path = settings.DATAPATH
    filenames = settings.NAME
    for filename in filenames:
        filepath.append(os.path.join(base_path, filename))
    return filepath


def init_schema(conn: sqlite3.Connection):
    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS areas (
                            area_code  TEXT PRIMARY KEY,
                            area_name  TEXT
                        );


                        CREATE TABLE IF NOT EXISTS postcode_map (
                            postcode   TEXT PRIMARY KEY,
                            area_code  TEXT NOT NULL,
                            FOREIGN KEY (area_code)
                                REFERENCES areas(area_code)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT
                        );

                        CREATE INDEX IF NOT EXISTS idx_postcode_map_area_code
                            ON postcode_map (area_code);

                        CREATE TABLE IF NOT EXISTS rent_stats_official (
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
                        
                            PRIMARY KEY (time_period, area_code),
                        
                            FOREIGN KEY (area_code)
                                REFERENCES areas(area_code)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT
                        );
                        CREATE INDEX IF NOT EXISTS idx_rent_area_time
                            ON rent_stats_official (area_code, time_period);

                        CREATE TABLE IF NOT EXISTS sales_transactions_official (
                            transaction_uuid  TEXT PRIMARY KEY,
                        
                            price             REAL NOT NULL,            
                            transaction_date  TEXT    NOT NULL,              
                        
                            postcode          TEXT,
                            property_type     TEXT CHECK (
                                property_type IS NULL OR property_type IN ('F','D','S','T','O')
                            ),
                            new_build         INTEGER CHECK (
                                new_build IS NULL OR new_build IN (0, 1)
                            ),
                            tenure            TEXT CHECK (
                                tenure IS NULL OR tenure IN ('L','F')
                            ),
                        
                            paon              TEXT,
                            saon              TEXT,
                        
                            FOREIGN KEY (postcode)
                                REFERENCES postcode_map(postcode)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_sales_official_date
                            ON sales_transactions_official (transaction_date);
                        
                        CREATE INDEX IF NOT EXISTS idx_sales_official_postcode
                            ON sales_transactions_official (postcode);
                        
                        CREATE INDEX IF NOT EXISTS idx_sales_official_filters_date
                            ON sales_transactions_official (property_type, new_build, tenure, transaction_date);
                        

                        CREATE TABLE IF NOT EXISTS sales_fk_rejects (
                            transaction_uuid TEXT PRIMARY KEY,
                            postcode         TEXT,
                            reason           TEXT
                        );

                        CREATE INDEX IF NOT EXISTS idx_sales_fk_rejects_reason ON sales_fk_rejects(reason);

                        CREATE TABLE IF NOT EXISTS rent_stats_user (
                            id            INTEGER PRIMARY KEY AUTOINCREMENT,
                            postcode      TEXT,
                            area_code     TEXT,
                            time_period   TEXT NOT NULL,
                            rent          REAL NOT NULL,
                            bedrooms      INTEGER,
                            property_type TEXT,
                            created_at    TEXT,
                            source        TEXT DEFAULT 'user'
                                CHECK (source IN ('user', 'survey', 'partner')),
                            uploader_id   INTEGER,
                        
                            FOREIGN KEY (postcode)
                                REFERENCES postcode_map (postcode)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT,
                        
                            FOREIGN KEY (area_code)
                                REFERENCES areas (area_code)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT
                        );
                            
                        CREATE TABLE IF NOT EXISTS sales_transactions_user (
                            id            INTEGER PRIMARY KEY AUTOINCREMENT,
                            postcode      TEXT,
                            area_code     TEXT,
                            time_period   TEXT NOT NULL,
                            price         REAL NOT NULL,
                            property_type TEXT,
                            created_at    TEXT,
                            source        TEXT DEFAULT 'user'
                                CHECK (source IN ('user', 'survey', 'partner')),
                            uploader_id   INTEGER,
                        
                            FOREIGN KEY (postcode)
                                REFERENCES postcode_map (postcode)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT,
                        
                            FOREIGN KEY (area_code)
                                REFERENCES areas (area_code)
                                ON UPDATE CASCADE
                                ON DELETE RESTRICT
                        );

                       """)

    conn.commit()


def generate_data_for_area_postcode(filepath: list, conn: sqlite3.Connection, chunk_size=200_000):
    sql_area = "INSERT OR IGNORE INTO areas(area_code) VALUES (?)"
    sql_pm = "INSERT OR REPLACE INTO postcode_map(postcode, area_code) VALUES (?, ?)"

    # ONSPD（ONS Postcode Directory）

    for chunk in pd.read_csv(filepath[0], usecols=['pcds', 'lad25cd'], chunksize=chunk_size):
        chunk = chunk.dropna(subset=["pcds", "lad25cd"])
        chunk["postcode"] = chunk["pcds"].map(norm_postcode)
        chunk["area_code"] = chunk["lad25cd"].astype(str)

        uniq_areas = [(x,) for x in chunk["area_code"].drop_duplicates().tolist()]
        conn.executemany(sql_area, uniq_areas)

        rows = list(zip(chunk["postcode"].tolist(), chunk["area_code"].tolist()))

        conn.executemany(sql_pm, rows)
        conn.commit()


def update_area_name(filepath: list, conn: sqlite3.Connection):
    # Price Index of Private Rents
    df_ons_pipr = pd.read_excel(filepath[7], sheet_name='Table 1', header=2)
    df_lookup = df_ons_pipr[["Area code", "Area name"]].dropna()
    df_lookup = df_lookup.drop_duplicates(subset=["Area code"])
    pairs = list(df_lookup.itertuples(index=False, name=None))

    sql_update = """
                 UPDATE areas
                 SET area_name = ?
                 WHERE area_code = ? \
                 """

    conn.executemany(sql_update, [(name, code) for code, name in pairs])

    conn.commit()


def generate_data_for_official_rent(filepath: list, conn: sqlite3.Connection):
    sql_rent = """
                INSERT OR REPLACE INTO rent_stats_official
                (time_period, area_code, region_or_country_name, index_value, annual_change,
                rental_price, index_one_bed, rental_price_one_bed, index_two_bed, rental_price_two_bed,
                index_three_bed, rental_price_three_bed, rental_price_detached,
                 rental_price_semidetached, rental_price_terraced, rental_price_flat_maisonette
                )VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               """
    valid_area_codes = {
        row[0] for row in conn.execute("SELECT area_code FROM areas")
    }
    # Price Index of Private Rents
    df_pipr = pd.read_excel(filepath[7], sheet_name='Table 1', header=2, usecols=column_name_pipr)

    df_pipr = df_pipr[df_pipr["Area code"].isin(valid_area_codes)]
    df_pipr["Time period"] = pd.to_datetime(df_pipr["Time period"], format="%b-%Y").dt.strftime("%Y-%m")
    df_pipr = df_pipr.replace('[x]', pd.NA)

    df_pipr[numeric_cols] = df_pipr[numeric_cols].apply(
        pd.to_numeric, errors="coerce"
    )

    rows = list(
        df_pipr[column_name_pipr].where(pd.notna(df_pipr[column_name_pipr]), None).itertuples(index=False, name=None))
    conn.executemany(sql_rent, rows)
    conn.commit()


def generate_data_for_official_sales(filepath: list, conn: sqlite3.Connection):
    sql_hmlr = """
                INSERT OR REPLACE INTO sales_transactions_official
                (transaction_uuid, price, transaction_date, postcode, property_type, new_build, tenure,
                paon, saon)VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               """
    sql_reject = """
                 INSERT INTO sales_fk_rejects(transaction_uuid, postcode, reason)
                 VALUES (?, ?, ?) \
                 """
    usecols = list(range(0, 16))
    valid_pc = {r[0] for r in conn.execute("SELECT postcode FROM postcode_map")}

    for file in filepath[1:7]:
        with open(file) as f:
            # HM Land Registry
            df_hmlr = pd.read_csv(f, usecols=usecols, header=None)
            df_hmlr.columns = column_name

            df_hmlr["transaction_uuid"] = (
                df_hmlr["transaction_uuid"]
                .astype(str)
                .str.strip("{}")
                .str.lower()
            )

            df_hmlr["postcode"] = df_hmlr["postcode"].map(norm_postcode)
            df_hmlr = df_hmlr.dropna(subset=["postcode"])

            bad_mask = ~df_hmlr["postcode"].isin(valid_pc)

            if bad_mask.any():
                rej = df_hmlr.loc[bad_mask, ["transaction_uuid", "postcode"]].copy()
                rej["reason"] = "postcode_not_in_postcode_map"
                conn.executemany(sql_reject, rej.itertuples(index=False, name=None))
                conn.commit()

            df_hmlr = df_hmlr.loc[~bad_mask].copy()

            df_hmlr["new_build"] = (
                df_hmlr["new_build"]
                .astype("string")
                .str.strip()
                .str.upper()
                .map({"Y": 1, "N": 0})
            ).astype("Int64")

            df_hmlr["transaction_date"] = pd.to_datetime(df_hmlr["transaction_date"]).dt.strftime("%Y-%m-%d")

            insert_cols = [
                "transaction_uuid", "price", "transaction_date", "postcode",
                "property_type", "new_build", "tenure", "paon", "saon"
            ]

            to_insert = df_hmlr[insert_cols].copy()
            to_insert = to_insert.astype("object").where(pd.notna(to_insert), None)

            rows = to_insert.itertuples(index=False, name=None)

            conn.executemany(sql_hmlr, rows)
            conn.commit()

def  main_database():
    settings = Settings()
    filepaths = file_loader(settings)

    db_dir = os.path.dirname(settings.DATABASE)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE)

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    init_schema(conn)
    create_table_logs(conn)
    create_table_users(conn)
    generate_data_for_area_postcode(filepaths, conn)
    update_area_name(filepaths, conn)
    generate_data_for_official_rent(filepaths, conn)
    generate_data_for_official_sales(filepaths, conn)

    conn.close()

def demo_db():
    settings = Settings()
    db_dir = os.path.dirname(settings.DATABASE_DEMO)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_DEMO)

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    init_schema(conn)
    create_table_logs(conn)
    create_table_users(conn)
    demo_data(conn)

    conn.commit()
    conn.close()

def demo_data(conn: sqlite3.Connection):
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



if __name__ == '__main__':
    # main_database()
    demo_db()

