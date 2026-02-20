import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.api.deps import get_conn
from app.services.service_rent_official import (get_rent_stats_official_one,
                                                get_rent_stats_official_series,
                                                get_rent_stats_official_latest,
                                                validate_yyyy_mm,
                                                get_rent_stats_official_availability)
from app.services.service_area import area_exists
from app.schemas.rent_stats_official import RentStatsOfficialOut, RentStatsAvailabilityOut
from app.schemas.errors import ErrorOut


router = APIRouter()

@router.get(
    "/rent-stats",
    response_model=RentStatsOfficialOut,
    responses={
        400: {"model": ErrorOut, "description": "Invalid query parameters (e.g., time_period format)."},
        404: {"model": ErrorOut, "description": "No data available for the given inputs."},
    },
)
def api_get_rent_stats(
    area_code: str,
    time_period: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        validate_yyyy_mm(time_period, "time_period")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = get_rent_stats_official_one(conn, area_code, time_period)
    if result is None:
        raise HTTPException(status_code=404, detail="No data available for the given inputs")

    return result


@router.get(
    "/areas/{area_code}/rent-stats",
    response_model=list[RentStatsOfficialOut],
    responses={
        400: {"model": ErrorOut, "description": "Invalid query parameters (format/range)."},
        404: {"model": ErrorOut, "description": "Area not found."},
    },
)
def api_get_rent_stats_series(
    area_code: str,
    from_: Optional[str] = Query(None, alias="from", description="Start time period (YYYY-MM)"),
    to: Optional[str] = Query(None, description="End time period (YYYY-MM)"),
    conn: sqlite3.Connection = Depends(get_conn),
):
    # 404: area not exists
    if not area_exists(conn, area_code):
        raise HTTPException(status_code=404, detail="Area not found")

    # 400: from/to format
    try:
        validate_yyyy_mm(from_, "from")
        validate_yyyy_mm(to, "to")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 400: from > to
    if from_ and to and from_ > to:
        raise HTTPException(status_code=400, detail="'from' must be <= 'to'")

    # 200: list (possibly empty)
    return get_rent_stats_official_series(conn, area_code, from_, to)


@router.get(
    "/areas/{area_code}/rent-stats/latest",
    response_model=RentStatsOfficialOut,
    responses={
        404: {"model": ErrorOut, "description": "Area not found, or no rent stats available."},
    },
)
def api_get_rent_stats_latest(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise HTTPException(404, "Area not found")

    result = get_rent_stats_official_latest(conn, area_code)

    if result is None:
        raise HTTPException(404, "No rent stats available")

    return result


@router.get(
    "/areas/{area_code}/rent-stats/availability",
    response_model=RentStatsAvailabilityOut,
    responses={
        404: {"model": ErrorOut, "description": "Area not found."},
    },
)
def api_get_rent_stats_availability(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise HTTPException(status_code=404, detail="Area not found")

    return get_rent_stats_official_availability(conn, area_code)