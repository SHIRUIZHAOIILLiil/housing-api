import sqlite3
from fastapi import APIRouter, Depends
from app.api.deps import get_conn


router = APIRouter()

@router.get("/db-check")
def check_db(conn: sqlite3.Connection = Depends(get_conn)):
    row = conn.execute("SELECT 1 AS ok").fetchone()
    return dict(row)
