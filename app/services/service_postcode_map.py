import sqlite3
from typing import Optional
from app.schemas.errors import NotFoundError, BadRequestError

def _norm_postcode(s: str) -> str:
    if s is None:
        raise BadRequestError("postcode is required")

    pc = s.strip().upper().replace(" ", "")
    if not pc:
        raise BadRequestError("postcode cannot be empty")

    # UK postcodes (after removing spaces) are typically 5-7 characters long;
    # Using lightweight validation here to prevent unusual input.
    if len(pc) < 5 or len(pc) > 7:
        raise BadRequestError("invalid postcode format")

    return pc

def _norm_query(q: Optional[str]) -> Optional[str]:
    if q is None:
        return None
    qq = q.strip().upper().replace(" ", "")
    # If a user sends a 'q' followed by spaces, treating it as 400 (or as None = return all).
    if not qq:
        raise BadRequestError("q cannot be empty")
    return qq

def get_postcode_map(conn: sqlite3.Connection, postcode:str):
    postcode = postcode.strip().upper().replace(" ", "")
    row = conn.execute(
        """
            select pm.postcode, pm.area_code, ac.area_name from postcode_map as pm join areas as ac
                on pm.area_code = ac.area_code
                where pm.postcode = ?
        """, (postcode,)
    ).fetchone()
    if not row:
        raise NotFoundError("Postcode not found")
    return dict(row)

def get_postcode_map_by_area_code(conn: sqlite3.Connection, area_code:str, limit: int):
    area_code = area_code.strip().upper().replace(" ", "")

    if not area_code:
        raise BadRequestError("area_code cannot be empty")

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