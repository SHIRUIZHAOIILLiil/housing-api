"""
Area lookup endpoints.

This router exposes read-only access to UK statistical areas used across the API.

Endpoints
- GET /areas
  List areas. Supports optional fuzzy query on name/code and pagination.
- GET /areas/{area_code}
  Get a single area by its code.
- GET /areas/{area_code}/postcodes
  List postcodes mapped to a given area code.

Notes
- These endpoints are read-only and backed by the reference tables imported from official datasets.
- Validation errors are returned as 422 (request schema/parameter validation).
- Domain errors (e.g., unknown area_code) are raised as NotFoundError and mapped to 404 by global handlers.
- Bad query parameters (e.g., malformed patterns) are raised as BadRequestError and mapped to 400.
"""

import sqlite3
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.services.service_area import list_areas, get_area, area_exists
from app.services.service_postcode_map import get_postcode_map_by_area_code
from app.schemas.areas import AreaOut
from app.schemas.postcode import PostcodeOut
from app.schemas.errors import ErrorOut, NotFoundError
router = APIRouter()

@router.get("", response_model=list[AreaOut], responses=COMMON_ERROR_RESPONSES)
def api_list_areas(
    q: str | None = Query(default=None, description="Fuzzy search by area name"),
    limit: int = Query(default=50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """List areas, with optional fuzzy search and pagination."""
    return list_areas(conn, q=q, limit=limit)


@router.get("/{area_code}", response_model=AreaOut, responses=COMMON_ERROR_RESPONSES)
def api_get_area(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    """Retrieve a single area by area_code."""
    return get_area(conn, area_code)

@router.get("/{area_code}/postcodes", response_model=list[PostcodeOut], responses=COMMON_ERROR_RESPONSES)
def api_postcode(
    area_code: str,
    limit: int = Query(default=50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),

):
    """List postcodes belonging to the specified area_code."""
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")
    return get_postcode_map_by_area_code(conn, area_code, limit)