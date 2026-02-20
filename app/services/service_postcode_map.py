import sqlite3
from typing import Optional

def get_postcode_map(conn: sqlite3.Connection, postcode:str):
    postcode = postcode.strip().upper().replace(" ", "")
    row = conn.execute(
        """
            select pm.postcode, pm.area_code, ac.area_name from postcode_map as pm join areas as ac
                on pm.area_code = ac.area_code
                where pm.postcode = ?
        """, (postcode,)
    ).fetchone()
    return dict(row) if row else None

def get_postcode_map_by_area_code(conn: sqlite3.Connection, area_code:str, limit: int):
    area_code = area_code.strip().upper().replace(" ", "")
    rows = conn.execute(
        """
            SELECT pm.postcode, pm.area_code, ac.area_name
            FROM postcode_map as pm join areas as ac
                on pm.area_code = ac.area_code
                where pm.area_code = ?
                limit ?
        """, (area_code, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def get_postcode_fuzzy_query(conn: sqlite3.Connection, q: Optional[str], limit: int):
    if q:
        rows = conn.execute(
            """
            SELECT pm.postcode, pm.area_code, ac.area_name
            FROM postcode_map as pm join areas as ac
            on pm.area_code = ac.area_code
            where pm.postcode like ?
            LIMIT ?
            """, (f"%{q}%", limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT pm.postcode, pm.area_code, ac.area_name
            FROM postcode_map as pm join areas as ac
            on pm.area_code = ac.area_code
            LIMIT ?
            """, (limit,),
        ).fetchall()

    return [dict(r)for r in rows]