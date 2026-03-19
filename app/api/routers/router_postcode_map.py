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
from fastapi import APIRouter, Depends, Query, Path
from typing import Optional

from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.services.service_postcode_map import get_postcode_map, get_postcode_fuzzy_query
from app.schemas.postcode import PostcodeOut

router = APIRouter()

@router.get(
    "/{postcode}",
    response_model=PostcodeOut,
    summary="Resolve one postcode",
    description="Normalize the supplied postcode and return its mapped administrative area.",
    responses=COMMON_ERROR_RESPONSES,
)
def get_postcode_areas(
        postcode: str = Path(..., description="Postcode to resolve.", examples=["LS29JT"]),
        conn: sqlite3.Connection = Depends(get_conn)
):
    return get_postcode_map(conn, postcode)

@router.get(
    "",
    response_model=list[PostcodeOut],
    summary="Fuzzy-search postcodes",
    description="Search postcode mappings using a fuzzy postcode fragment. The search ignores spaces and casing.",
    responses=COMMON_ERROR_RESPONSES,
)
def get_postcode_fuzzy(
        q: Optional[str] = Query(default=None, description="Fuzzy search by postcode.", examples=["LS29"]),
        limit: int = Query(default=50, ge=1, le=200, description="Maximum number of rows to return.", examples=[50]),
        conn: sqlite3.Connection = Depends(get_conn),
):
    return get_postcode_fuzzy_query(conn, q, limit)
