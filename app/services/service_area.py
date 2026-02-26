"""
Service layer for area resources.

Responsibilities
- Read-only access to the areas reference table.
- Validation of inputs that are not covered by Pydantic constraints (if any).
- Conversion of sqlite3.Row results into plain dicts / Pydantic models.

Error handling
- Raise NotFoundError when an area_code does not exist.
- Raise BadRequestError for malformed queries or parameters if the router allows free-text search.
"""
import sqlite3
from typing import Optional
from app.schemas.errors import NotFoundError

def list_areas(conn: sqlite3.Connection, q: Optional[str], limit: int):
    if q:
        rows = conn.execute(
            """
            SELECT area_code, area_name
            FROM areas
            WHERE area_name LIKE ? COLLATE NOCASE
            ORDER BY area_name
            LIMIT ?
            """,
            (f"%{q}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT area_code, area_name
            FROM areas
            ORDER BY area_name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(r) for r in rows]


def get_area(conn: sqlite3.Connection, area_code: str):
    row = conn.execute(
        """
        SELECT area_code, area_name
        FROM areas
        WHERE area_code = ?
        """,
        (area_code,),
    ).fetchone()
    if not row:
        raise NotFoundError("Area not found")

    return dict(row)

def area_exists(conn: sqlite3.Connection, area_code: str):
    row = conn.execute(
        """
        SELECT area_code FROM areas WHERE area_code = ?
        """,
        (area_code,),
    ).fetchone()
    return row is not None
