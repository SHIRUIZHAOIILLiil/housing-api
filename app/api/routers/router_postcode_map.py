"""
Postcode mapping endpoints.

These endpoints provide postcode -> area mapping, used for both official and user-generated records.

Endpoints
- GET /postcode_map
  Fuzzy search postcodes and return their mapped area_code(s).
- GET /postcode_map/{postcode}
  Get mapping details for a single postcode.

Notes
- Postcode normalization (spacing/casing) is typically handled in the service layer.
- Unknown postcode should raise NotFoundError (mapped to 404).
- Validation errors are returned as 422.
"""
import sqlite3
from fastapi import APIRouter, Depends, Query
from typing import Optional

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
        q: Optional[str] = Query(default=None, description="Fuzzy search by postcode"),
        limit: int = Query(default=50, ge=1, le=200),
        conn: sqlite3.Connection = Depends(get_conn),
):
    return get_postcode_fuzzy_query(conn, q, limit)