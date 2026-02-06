import os, sqlite3, re
import pandas as pd
from app import Config


column_name = [                 "price_gbp",
                                "transfer_date",
                                "postcode",
                                "property_type",
                                "is_new_build",
                                "tenure",
                                "PAON",
                                "SAON",
                                "Street",
                                "Locality",
                                "Town/City",
                                "District",
                                "County",
                                "PPD Category",
                                "Record Status"]
def norm_postcode(s: str) -> str:
    return re.sub(r"\s+", "", str(s).strip().upper())

def file_loader(config: Config):
    filepath = []
    base_path = config.DATAPATH
    filenames = config.NAME
    for filename in filenames:
        filepath.append(os.path.join(base_path, filename))
    return filepath

def create_database():
    conn = sqlite3.connect("housing.db")
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS postcode_map (
        postcode TEXT PRIMARY KEY,
        area_code  TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def generate_table_area(filepath: list, db_path: str, chunk_size=200_000):
    usecols = []
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    sql = "INSERT OR REPLACE INTO postcode_map(postcode, area_code) VALUES (?, ?)"

    for i in range(1,16):
        usecols.append(i)
    # ONSPD（ONS Postcode Directory）

    # df_ons_pd = pd.read_csv(filepath[0], usecols=['pcds', 'lad25cd'])
    for chunk in pd.read_csv(filepath[0], usecols=['pcds', 'lad25cd'], chunksize=chunk_size):
        chunk = chunk.dropna(subset=["pcds", "lad25cd"])
        chunk["postcode"] = chunk["pcds"].map(norm_postcode)
        chunk["area_code"] = chunk["lad25cd"].astype(str)
        rows = list(zip(chunk["postcode"].tolist(), chunk["area_code"].tolist()))

        conn.executemany(sql, rows)
        conn.commit()

    conn.close()
    # for file in filepath[1:7]:
    #     with open(file) as f:
    #         # HM Land Registry
    #         df_hmlr = pd.read_csv(f, usecols=usecols)
    #         df_hmlr.columns = column_name

    # Price Index of Private Rents
    # df_ons_pipr = pd.read_excel(filepath[7], sheet_name='Table 1')



if __name__ == '__main__':
    config = Config()
    filepaths = file_loader(config)
    create_database()
    generate_table_area(filepaths, "housing.db")
