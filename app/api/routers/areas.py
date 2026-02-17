import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_conn
from app.services.area_service import list_areas, get_area
from app.schemas.areas import AreaOut

router = APIRouter()

@router.get("", response_model=list[AreaOut])
def api_list_areas(
    q: str | None = Query(default=None, description="Fuzzy search by area name"),
    limit: int = Query(default=50, ge=1, le=2000),
    conn: sqlite3.Connection = Depends(get_conn),
):
    return list_areas(conn, q=q, limit=limit)


@router.get("/{area_code}", response_model=AreaOut)
def api_get_area(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    area = get_area(conn, area_code)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area
