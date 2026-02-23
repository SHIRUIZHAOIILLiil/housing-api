import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.services.service_postcode_map import get_postcode_map, get_postcode_fuzzy_query
from app.schemas.postcode import PostcodeOut

router = APIRouter()

@router.get("/{postcode}", response_model=PostcodeOut, responses=COMMON_ERROR_RESPONSES)
def get_postcode_areas(
        postcode: str,
        conn: sqlite3.Connection = Depends(get_conn)
):
    return get_postcode_map(conn, postcode)

@router.get("", response_model=list[PostcodeOut], responses=COMMON_ERROR_RESPONSES)
def get_postcode_fuzzy(
        q: str | None = Query(default=None, description="Fuzzy search by postcode"),
        limit: int = Query(default=50, ge=1, le=200),
        conn: sqlite3.Connection = Depends(get_conn),
):
    return get_postcode_fuzzy_query(conn, q, limit)