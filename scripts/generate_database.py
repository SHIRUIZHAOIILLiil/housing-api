import os
import sqlite3
import re
import pandas as pd
from app.core.config import Settings

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
                       CREATE TABLE IF NOT EXISTS areas
                       (
                           area_code
                           TEXT
                           PRIMARY
                           KEY,
                           area_name
                           TEXT
                       );

                       CREATE TABLE IF NOT EXISTS postcode_map
                       (
                           postcode
                           TEXT
                           PRIMARY
                           KEY,
                           area_code
                           TEXT
                           NOT
                           NULL,
                           FOREIGN
                           KEY
                       (
                           area_code
                       ) REFERENCES areas
                       (
                           area_code
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT
                           );

                       CREATE INDEX IF NOT EXISTS idx_postcode_map_area_code
                           ON postcode_map(area_code);

                       CREATE TABLE IF NOT EXISTS rent_stats_official
                       (
                           time_period
                           TEXT
                           NOT
                           NULL,
                           area_code
                           TEXT
                           NOT
                           NULL,
                           region_or_country_name
                           TEXT
                           NOT
                           NULL,

                           index_value
                           REAL,
                           annual_change
                           REAL,
                           rental_price
                           REAL,
                           index_one_bed
                           REAL,
                           rental_price_one_bed
                           REAL,
                           index_two_bed
                           REAL,
                           rental_price_two_bed
                           REAL,
                           index_three_bed
                           REAL,
                           rental_price_three_bed
                           REAL,
                           rental_price_detached
                           REAL,
                           rental_price_semidetached
                           REAL,
                           rental_price_terraced
                           REAL,
                           rental_price_flat_maisonette
                           REAL,

                           PRIMARY
                           KEY
                       (
                           time_period,
                           area_code
                       ),
                           FOREIGN KEY
                       (
                           area_code
                       )
                           REFERENCES areas
                       (
                           area_code
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT
                           );
                       CREATE INDEX IF NOT EXISTS idx_rent_area_time ON rent_stats_official(area_code, time_period);


                       CREATE TABLE IF NOT EXISTS sales_transactions_official
                       (
                           transaction_uuid
                           TEXT
                           PRIMARY
                           KEY,
                           price
                           REAL
                           NOT
                           NULL,
                           transaction_date
                           TEXT
                           NOT
                           NULL,
                           postcode
                           TEXT,
                           property_type
                           TEXT
                           CHECK (
                           property_type
                           IS
                           NULL
                           OR
                           property_type
                           IN
                       (
                           'F',
                           'D',
                           'S',
                           'T',
                           'O'
                       )),
                           new_build INTEGER CHECK
                       (
                           new_build
                           IS
                           NULL
                           OR
                           new_build
                           IN
                       (
                           0,
                           1
                       )),
                           tenure TEXT CHECK
                       (
                           tenure
                           IS
                           NULL
                           OR
                           tenure
                           IN
                       (
                           'L',
                           'F'
                       )),
                           paon TEXT,
                           saon TEXT,
                           FOREIGN KEY
                       (
                           postcode
                       )
                           REFERENCES postcode_map
                       (
                           postcode
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT
                           );

                       CREATE TABLE IF NOT EXISTS sales_fk_rejects
                       (
                           transaction_uuid
                           TEXT
                           PRIMARY
                           KEY,
                           postcode
                           TEXT,
                           reason
                           TEXT
                       );

                       CREATE INDEX IF NOT EXISTS idx_sales_fk_rejects_reason ON sales_fk_rejects(reason);

                       CREATE TABLE IF NOT EXISTS rent_stats_user
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           postcode
                           TEXT,
                           area_code
                           TEXT,
                           time_period
                           TEXT
                           NOT
                           NULL,
                           rent
                           REAL
                           NOT
                           NULL,
                           bedrooms
                           INTEGER,
                           property_type
                           TEXT,
                           created_at
                           TEXT,
                           source
                           TEXT
                           DEFAULT
                           'user'
                           CHECK (
                           source
                           IN
                       (
                           'user',
                           'survey',
                           'partner'
                       )),
                           FOREIGN KEY
                       (
                           postcode
                       )
                           REFERENCES postcode_map
                       (
                           postcode
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT,
                           FOREIGN KEY
                       (
                           area_code
                       )
                           REFERENCES areas
                       (
                           area_code
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT

                           );
                       CREATE TABLE IF NOT EXISTS sales_transactions_user
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           postcode
                           TEXT,
                           area_code
                           TEXT,
                           time_period
                           TEXT
                           NOT
                           NULL,
                           price
                           REAL
                           NOT
                           NULL,
                           property_type
                           TEXT,
                           created_at
                           TEXT,
                           source
                           TEXT
                           DEFAULT
                           'user'
                           CHECK (
                           source
                           IN
                       (
                           'user',
                           'survey',
                           'partner'
                       )),
                           FOREIGN KEY
                       (
                           postcode
                       )
                           REFERENCES postcode_map
                       (
                           postcode
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT,
                           FOREIGN KEY
                       (
                           area_code
                       )
                           REFERENCES areas
                       (
                           area_code
                       )
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT


                           );
                       CREATE INDEX IF NOT EXISTS idx_sales_postcode ON sales_transactions_official(postcode);
                       CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions_official(transaction_date);



                       """)



    conn.commit()


def generate_tables(filepath: list, conn: sqlite3.Connection, chunk_size=200_000):
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


def generate_rent_table(filepath: list, conn: sqlite3.Connection):
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


def generate_hmlr_table(filepath: list, conn: sqlite3.Connection):
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


if __name__ == '__main__':
    settings = Settings()
    filepaths = file_loader(settings)

    db_dir = os.path.dirname(settings.DATABASE)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE)

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    init_schema(conn)
    generate_tables(filepaths, conn)
    update_area_name(filepaths, conn)
    generate_rent_table(filepaths, conn)
    generate_hmlr_table(filepaths, conn)
    conn.close()
