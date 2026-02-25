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
    return list_areas(conn, q=q, limit=limit)


@router.get("/{area_code}", response_model=AreaOut, responses=COMMON_ERROR_RESPONSES)
def api_get_area(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    return get_area(conn, area_code)

@router.get("/{area_code}/postcodes", response_model=list[PostcodeOut], responses=COMMON_ERROR_RESPONSES)
def api_postcode(
    area_code: str,
    limit: int = Query(default=50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),

):
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")
    return get_postcode_map_by_area_code(conn, area_code, limit)