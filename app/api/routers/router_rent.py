"""
Official rent statistics endpoints.

This router exposes read-only access to ONS-derived rental statistics aggregated by area and time period.

Endpoints
- GET /rent_stats_official/rent-stats
  Retrieve an aggregated rent stats point for (area_code, time_period) with optional filters.
- GET /rent_stats_official/areas/{area_code}/rent-stats
  Retrieve a time-series for one area_code over a period range.
- GET /rent_stats_official/areas/{area_code}/rent-stats/latest
  Retrieve the latest available point for an area_code.
- GET /rent_stats_official/areas/{area_code}/rent-stats/availability
  Retrieve min/max available months for an area_code.
- GET /rent_stats_official/areas/{area_code}/rent-trend.png
  Render a trend plot (PNG) for an area_code over a period range and metric selection.
- GET /rent_stats_official/areas/rent-trend.png
  Render a trend plot (PNG) where the area is provided by name (fuzzy match).

Notes
- These endpoints are read-only; no mutation of official tables is allowed.
- Image endpoints return binary PNG responses; failures still follow the JSON error contract via global handlers.
- Unknown areas/periods should raise NotFoundError (404); malformed periods should raise BadRequestError (400).
- Validation errors are returned as 422.
"""

import sqlite3
import re
from fastapi import APIRouter, Depends, Query, Response, Path
from typing import Optional, Literal
from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.services.service_rent_official import (get_rent_stats_official_one,
                                                get_rent_stats_official_series,
                                                get_rent_stats_official_latest,
                                                validate_yyyy_mm,
                                                get_rent_stats_official_availability,
                                                get_rent_map_summary,
                                                build_rent_trend_png,)
from app.services.service_area import area_exists
from app.schemas.rent_stats_official import RentStatsOfficialOut, RentStatsAvailabilityOut, RentMapSummaryOut
from app.schemas.errors import BadRequestError, NotFoundError, ErrorOut


router = APIRouter()

YYYY_MM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

@router.get(
    "/map/summary",
    response_model=RentMapSummaryOut,
    summary="Load a rent map snapshot",
    description="Return one monthly snapshot of official rent values across all available areas. This endpoint powers the standalone /map page.",
    responses=COMMON_ERROR_RESPONSES,
)
def api_get_rent_map_summary(
    time_period: Optional[str] = Query(None, description="Snapshot month (YYYY-MM). Defaults to latest available.", examples=["2017-06"]),
    metric: Literal["rental_price", "index_value", "annual_change"] = "rental_price",
    bedrooms: Literal["overall", "1", "2", "3"] = "overall",
    conn: sqlite3.Connection = Depends(get_conn),
):
    return get_rent_map_summary(
        conn,
        time_period=time_period,
        metric=metric,
        bedrooms=bedrooms,
    )

@router.get(
    "/rent-stats",
    response_model=RentStatsOfficialOut,
    summary="Get one official rent point",
    description="Return one official rent-statistics observation for a single area and month.",
    responses=COMMON_ERROR_RESPONSES,
)
def api_get_rent_stats(
    area_code: str = Query(..., description="Administrative area code.", examples=["E08000035"]),
    time_period: str = Query(..., description="Monthly observation period in YYYY-MM format.", examples=["2017-06"]),
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
    response_model=list[RentStatsOfficialOut],
    summary="Get an official rent series",
    description="Return the official rent-statistics time series for one area, optionally constrained by a month range.",
    responses=COMMON_ERROR_RESPONSES,
)
def api_get_rent_stats_series(
    area_code: str = Path(..., description="Administrative area code.", examples=["E08000035"]),
    from_: Optional[str] = Query(None, alias="from", description="Start time period (YYYY-MM).", examples=["2017-02"]),
    to: Optional[str] = Query(None, description="End time period (YYYY-MM).", examples=["2017-06"]),
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
    summary="Get the latest official rent point",
    description="Return the most recent official rent-statistics observation for one area.",
    responses={
        **COMMON_ERROR_RESPONSES,
        404: {"model": ErrorOut, "description": "Area not found, or no rent stats available."},
    },
)
def api_get_rent_stats_latest(
    area_code: str = Path(..., description="Administrative area code.", examples=["E08000035"]),
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
    summary="Get rent-series availability",
    description="Return the earliest and latest available official rent months for one area.",
    responses={
        **COMMON_ERROR_RESPONSES,
        404: {"model": ErrorOut, "description": "Area not found."},
    },
)
def api_get_rent_stats_availability(
    area_code: str = Path(..., description="Administrative area code.", examples=["E08000035"]),
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not area_exists(conn, area_code):
        raise NotFoundError("Area not found")

    return get_rent_stats_official_availability(conn, area_code)


@router.get("/areas/{area_code}/rent-trend.png",
            response_class=Response,
            summary="Render a rent trend PNG",
            description="Render a server-side PNG chart for one area's official rent series.",
            responses={200: {"content": {"image/png": {}}, "description": "PNG image"}, **COMMON_ERROR_RESPONSES,},
            )
def api_get_rent_trend_plot(
    area_code: str = Path(..., description="Administrative area code.", examples=["E08000035"]),
    from_: Optional[str] = Query(None, alias="from", description="Start time period (YYYY-MM).", examples=["2017-02"]),
    to: Optional[str] = Query(None, description="End time period (YYYY-MM).", examples=["2017-06"]),
    metric: Literal["rental_price", "index_value", "annual_change"] = "rental_price",
    bedrooms: Literal["overall", "1", "2", "3"] = "overall",
    conn: sqlite3.Connection = Depends(get_conn),
):

    png = build_rent_trend_png(
        conn,
        area_code=area_code,
        from_=from_,
        to=to,
        metric=metric,
        bedrooms=bedrooms,
    )
    return Response(content=png, media_type="image/png")

@router.get("/areas/rent-trend.png",
            response_class=Response,
            summary="Render a rent trend PNG by area name",
            description="Render a server-side PNG chart where the area is selected by a fuzzy area name query.",
            responses={200: {"content": {"image/png": {}}, "description": "PNG image"}, **COMMON_ERROR_RESPONSES,},)
def api_rent_trend_by_name(
    area: str = Query(..., description="Area name, e.g. Leeds.", examples=["Leeds"]),
    from_: Optional[str] = Query(None, alias="from", description="Start time period (YYYY-MM).", examples=["2017-02"]),
    to: Optional[str] = Query(None, description="End time period (YYYY-MM).", examples=["2017-06"]),
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

    png = build_rent_trend_png(
        conn,
        area_code=area_code,
        from_=from_,
        to=to,
        metric=metric,
        bedrooms=bedrooms,
    )
    return Response(content=png, media_type="image/png")
