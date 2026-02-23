import sqlite3, re
from fastapi import APIRouter, Depends, Query, Response
from typing import Optional, Literal
from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.services.service_rent_official import (get_rent_stats_official_one,
                                                get_rent_stats_official_series,
                                                get_rent_stats_official_latest,
                                                validate_yyyy_mm,
                                                get_rent_stats_official_availability,
                                                build_rent_trend_png,)
from app.services.service_area import area_exists
from app.schemas.rent_stats_official import RentStatsOfficialOut, RentStatsAvailabilityOut
from app.schemas.errors import BadRequestError, NotFoundError, ErrorOut


router = APIRouter()

YYYY_MM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

@router.get(
    "/rent-stats",
    response_model=RentStatsOfficialOut, responses=COMMON_ERROR_RESPONSES )
def api_get_rent_stats(
    area_code: str,
    time_period: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")

    validate_yyyy_mm(time_period, "time_period")

    result = get_rent_stats_official_one(conn, area_code, time_period)
    if result is None:
        raise NotFoundError("No data available for the given inputs")

    return result


@router.get(
    "/areas/{area_code}/rent-stats",
    response_model=list[RentStatsOfficialOut], responses=COMMON_ERROR_RESPONSES )
def api_get_rent_stats_series(
    area_code: str,
    from_: Optional[str] = Query(None, alias="from", description="Start time period (YYYY-MM)"),
    to: Optional[str] = Query(None, description="End time period (YYYY-MM)"),
    conn: sqlite3.Connection = Depends(get_conn),
):
    # 404: area not exists
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")

    # 400: from/to format
    validate_yyyy_mm(from_, "from")
    validate_yyyy_mm(to, "to")

    if from_ and to and from_ > to:
        raise BadRequestError("'from' must be <= 'to'")

    # 200: list (possibly empty)
    return get_rent_stats_official_series(conn, area_code, from_, to)


@router.get(
    "/areas/{area_code}/rent-stats/latest",
    response_model=RentStatsOfficialOut,
    responses={
        **COMMON_ERROR_RESPONSES,
        404: {"model": ErrorOut, "description": "Area not found, or no rent stats available."},
    },
)
def api_get_rent_stats_latest(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")

    result = get_rent_stats_official_latest(conn, area_code)

    if result is None:
        raise NotFoundError("No rent stats available")

    return result


@router.get(
    "/areas/{area_code}/rent-stats/availability",
    response_model=RentStatsAvailabilityOut,
    responses={
        **COMMON_ERROR_RESPONSES,
        404: {"model": ErrorOut, "description": "Area not found."},
    },
)
def api_get_rent_stats_availability(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")

    return get_rent_stats_official_availability(conn, area_code)


@router.get("/areas/{area_code}/rent-trend.png",
            response_class=Response,
            responses={200: {"content": {"image/png": {}}, "description": "PNG image"}, **COMMON_ERROR_RESPONSES,},
            )
def api_get_rent_trend_plot(
    area_code: str,
    from_period: str = "2015-01",
    to_period: str = "2025-12",
    metric: Literal["rental_price", "index_value", "annual_change"] = "rental_price",
    bedrooms: Literal["overall", "1", "2", "3"] = "overall",
    conn: sqlite3.Connection = Depends(get_conn),
):
    # 400: validate periods
    validate_yyyy_mm(from_period, "from_period")
    validate_yyyy_mm(to_period, "to_period")
    if from_period > to_period:
        raise BadRequestError("'from_period' must be <= 'to_period'.")


    png = build_rent_trend_png(
        conn,
        area_code=area_code,
        from_period=from_period,
        to_period=to_period,
        metric=metric,
        bedrooms=bedrooms,
    )
    return Response(content=png, media_type="image/png")

@router.get("/areas/rent-trend.png",
            response_class=Response,
            responses={200: {"content": {"image/png": {}}, "description": "PNG image"}, **COMMON_ERROR_RESPONSES,},)
def api_rent_trend_by_name(
    area: str = Query(..., description="Area name, e.g. Leeds"),
    from_period: str = "2020-01",
    to_period: str = "2025-12",
    metric: Literal["rental_price", "index_value", "annual_change"] = "rental_price",
    bedrooms: Literal["overall", "1", "2", "3"] = "overall",
    conn: sqlite3.Connection = Depends(get_conn),
):
    rows = conn.execute(
        """
        SELECT area_code, area_name
        FROM areas
        WHERE LOWER(area_name) LIKE LOWER(?)
        LIMIT 3
        """,
        (f"%{area}%",),
    ).fetchall()

    if not rows:
        raise NotFoundError("Area not found")

    if len(rows) > 1:
        names = [r["area_name"] for r in rows]
        raise BadRequestError(f"Ambiguous area name. Matches: {names}. Please use area_code instead.")

    area_code = rows[0]["area_code"]

    validate_yyyy_mm(from_period, "from_period")
    validate_yyyy_mm(to_period, "to_period")

    if from_period > to_period:
        raise BadRequestError("'from_period' must be <= 'to_period'.")
    png = build_rent_trend_png(
        conn,
        area_code=area_code,
        from_period=from_period,
        to_period=to_period,
        metric=metric,
        bedrooms=bedrooms,
    )
    return Response(content=png, media_type="image/png")