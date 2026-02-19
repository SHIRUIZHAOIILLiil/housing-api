import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_conn
from app.services.postcode_map_service import get_postcode_map, get_postcode_fuzzy_query
from app.schemas.postcode import PostcodeOut

router = APIRouter()

@router.get("/{postcode}", response_model=PostcodeOut)
def get_postcode_areas(
        postcode: str,
        conn: sqlite3.Connection = Depends(get_conn)
):
    postcode_map = get_postcode_map(conn, postcode)
    if postcode_map is None:
        raise HTTPException(status_code=404, detail="Postcode not found")
    return postcode_map

@router.get("", response_model=list[PostcodeOut])
def get_postcode_fuzzy(
        q: str | None = Query(default=None, description="Fuzzy search by postcode"),
        limit: int = Query(default=50, ge=1, le=200),
        conn: sqlite3.Connection = Depends(get_conn),
):
    q = q.strip().upper().replace(" ", "")
    results = get_postcode_fuzzy_query(conn, q, limit)
    if results is None:
        raise HTTPException(status_code=404, detail="Postcode not found")
    return results