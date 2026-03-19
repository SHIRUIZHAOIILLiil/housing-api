"""
Service layer for official rental statistics.

Responsibilities
- Read-only queries over the ONS rental stats table.
- Support optional domain filters (e.g., bedrooms/property_type/metric) where applicable.
- Implement availability queries (min/max time_period) for user guidance and client-side validation.
- Generate plot data and render a PNG chart for trend endpoints.

Implementation notes
- time_period is treated as YYYY-MM (or derived from YYYY-MM-DD where applicable).
- Services should consistently validate and normalize time range inputs before querying.
- Prefer returning plain dicts/Pydantic models; do not leak sqlite3.Row outside the service layer.

Error handling
- Raise NotFoundError when area/time ranges have no matching data.
- Raise BadRequestError when time_period format or range is invalid.
"""
import matplotlib
matplotlib.use("Agg")
import sqlite3
import re
import io
import matplotlib.pyplot as plt
from typing import Optional, List, Literal
from app.schemas.rent_stats_official import (
    RentStatsOfficialOut,
    BedStats,
    OverallStats,
    PropertyTypePrices,
    RentStatsAvailabilityOut,
    RentMapPointOut,
    RentMapSummaryOut,
)
from app.schemas.errors import BadRequestError, NotFoundError, UnprocessableEntityError

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


Metric = Literal["rental_price", "index_value", "annual_change"]
Bedroom = Literal["overall", "1", "2", "3"]

def _bed(index, price) -> Optional[BedStats]:
    if index is None and price is None:
        return None
    return BedStats(index=index, rental_price=price)

def _pick_column(metric: Metric, bedrooms: Bedroom) -> str:
    if bedrooms == "overall":
        return metric

    if metric == "annual_change":
        raise UnprocessableEntityError("annual_change is only available for overall in the official dataset.")

    if bedrooms == "1":
        return "rental_price_one_bed" if metric == "rental_price" else "index_one_bed"
    if bedrooms == "2":
        return "rental_price_two_bed" if metric == "rental_price" else "index_two_bed"
    if bedrooms == "3":
        return "rental_price_three_bed" if metric == "rental_price" else "index_three_bed"

    raise ValueError("Invalid bedrooms option.")

def validate_yyyy_mm(value: Optional[str], field_name: str) -> None:
    if value is None:
        return
    if not YYYY_MM_RE.match(value):
        raise UnprocessableEntityError(f"Invalid {field_name}. Expected format YYYY-MM.")


def row_to_rent_stats_official(row: sqlite3.Row) -> RentStatsOfficialOut:
    return RentStatsOfficialOut(
        time_period=row["time_period"],
        area_code=row["area_code"],
        region_or_country_name=row["region_or_country_name"],

        overall=OverallStats(
            index=row["index_value"],
            rental_price=row["rental_price"],
            annual_change=row["annual_change"],
        ),

        one_bed=_bed(row["index_one_bed"], row["rental_price_one_bed"]),
        two_bed=_bed(row["index_two_bed"], row["rental_price_two_bed"]),
        three_bed=_bed(row["index_three_bed"], row["rental_price_three_bed"]),

        property_prices=PropertyTypePrices(
                detached=row["rental_price_detached"],
                semidetached=row["rental_price_semidetached"],
                terraced=row["rental_price_terraced"],
                flat_maisonette=row["rental_price_flat_maisonette"],
        )
    )

def get_rent_stats_official_one(
    conn: sqlite3.Connection,
    area_code: str,
    time_period: str,
) -> Optional[RentStatsOfficialOut]:

    row = conn.execute(
        """
        SELECT *
        FROM rent_stats_official
        WHERE area_code = ? AND time_period = ?
        """,
        (area_code, time_period),
    ).fetchone()

    if row is None:
        return None

    return row_to_rent_stats_official(row)

def get_rent_stats_official_series(
    conn: sqlite3.Connection,
    area_code: str,
    from_: Optional[str] = None,
    to: Optional[str] = None,
) -> List[RentStatsOfficialOut]:

    where = ["area_code = ?"]
    params = [area_code]

    validate_yyyy_mm(from_, "from")
    validate_yyyy_mm(to, "to")
    if from_ and to and from_ > to:
        raise BadRequestError("'from' must be <= 'to'")

    if from_:
        where.append("time_period >= ?")
        params.append(from_)

    if to:
        where.append("time_period <= ?")
        params.append(to)

    sql = f"""
        SELECT *
        FROM rent_stats_official
        WHERE {' AND '.join(where)}
        ORDER BY time_period ASC
    """

    rows = conn.execute(sql, params).fetchall()

    return [row_to_rent_stats_official(r) for r in rows]


def get_rent_stats_official_latest(
    conn: sqlite3.Connection,
    area_code: str,
) -> Optional[RentStatsOfficialOut]:

    row = conn.execute(
        """
        SELECT *
        FROM rent_stats_official
        WHERE area_code = ?
        ORDER BY time_period DESC
        LIMIT 1
        """,
        (area_code,),
    ).fetchone()

    if row is None:
        return None

    return row_to_rent_stats_official(row)

def get_rent_stats_official_availability(
    conn: sqlite3.Connection,
    area_code: str
) -> RentStatsAvailabilityOut:
    row = conn.execute(
        """
        SELECT
            MIN(time_period) AS min_time_period,
            MAX(time_period) AS max_time_period,
            COUNT(*) AS count
        FROM rent_stats_official
        WHERE area_code = ?
        """,
        (area_code,),
    ).fetchone()

    return RentStatsAvailabilityOut(
        area_code=area_code,
        min_time_period=row["min_time_period"],
        max_time_period=row["max_time_period"],
        count=int(row["count"] or 0),
    )


def get_rent_map_summary(
    conn: sqlite3.Connection,
    time_period: Optional[str] = None,
    metric: Metric = "rental_price",
    bedrooms: Bedroom = "overall",
) -> RentMapSummaryOut:
    validate_yyyy_mm(time_period, "time_period")
    col = _pick_column(metric, bedrooms)

    availability = conn.execute(
        """
        SELECT
            MIN(time_period) AS min_time_period,
            MAX(time_period) AS max_time_period
        FROM rent_stats_official
        """
    ).fetchone()

    max_time_period = availability["max_time_period"] if availability else None
    min_time_period = availability["min_time_period"] if availability else None

    if max_time_period is None:
        raise NotFoundError("No official rent data available")

    resolved_time_period = time_period or max_time_period

    rows = conn.execute(
        f"""
        SELECT
            rs.area_code,
            COALESCE(a.area_name, rs.area_code) AS area_name,
            rs.region_or_country_name,
            rs.time_period,
            {col} AS value,
            rs.rental_price,
            rs.index_value,
            rs.annual_change
        FROM rent_stats_official AS rs
        LEFT JOIN areas AS a
            ON a.area_code = rs.area_code
        WHERE rs.time_period = ?
          AND {col} IS NOT NULL
        ORDER BY value DESC, area_name ASC, rs.area_code ASC
        """,
        (resolved_time_period,),
    ).fetchall()

    if not rows:
        raise NotFoundError("No rent map data available for the given inputs")

    return RentMapSummaryOut(
        requested_time_period=time_period,
        resolved_time_period=resolved_time_period,
        min_time_period=min_time_period,
        max_time_period=max_time_period,
        metric=metric,
        bedrooms=bedrooms,
        item_count=len(rows),
        items=[
            RentMapPointOut(
                area_code=row["area_code"],
                area_name=row["area_name"],
                region_or_country_name=row["region_or_country_name"],
                time_period=row["time_period"],
                value=float(row["value"]),
                rental_price=float(row["rental_price"]) if row["rental_price"] is not None else None,
                index_value=float(row["index_value"]) if row["index_value"] is not None else None,
                annual_change=float(row["annual_change"]) if row["annual_change"] is not None else None,
            )
            for row in rows
        ],
    )


def build_rent_trend_png(
    conn: sqlite3.Connection,
    area_code: str,
    from_: str,
    to: str,
    metric: Metric = "rental_price",
    bedrooms: Bedroom = "overall",
) -> bytes:
    col = _pick_column(metric, bedrooms)

    validate_yyyy_mm(from_, "from")
    validate_yyyy_mm(to, "to")
    if from_ and to and from_ > to:
        raise BadRequestError("'from' must be <= 'to'")

    rows = conn.execute(
        f"""
        SELECT time_period, {col} AS value, region_or_country_name
        FROM rent_stats_official
        WHERE area_code = ?
          AND time_period >= ?
          AND time_period <= ?
        ORDER BY time_period ASC
        """,
        (area_code, from_, to),
    ).fetchall()

    if not rows:
        raise NotFoundError("No data available for the given inputs")

    # Filter out points where the value is NULL (for example, many early versions of annual_change were null).
    x: List[str] = []
    y: List[float] = []
    region_name = rows[0]["region_or_country_name"] if rows[0]["region_or_country_name"] else area_code
    for r in rows:
        if r["value"] is None:
            continue
        x.append(r["time_period"])
        y.append(float(r["value"]))

    if not y:
        raise NotFoundError("No usable data in range")

    # Drawing: Returns PNG bytes
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)

    ax.plot(x, y)

    # x-axis scale: Reduce density + rotation
    step = max(1, len(x) // 12)  # A maximum of approximately 12 tags can be displayed.
    ax.set_xticks(range(0, len(x), step))
    ax.set_xticklabels([x[i] for i in range(0, len(x), step)], rotation=45, ha="right")

    ax.set_xlabel("Month")
    ax.set_ylabel(metric)

    # Title: Shorten and add line breaks to avoid overflow.
    title_metric = f"{metric} ({'overall' if bedrooms == 'overall' else bedrooms + '-bed'})"
    ax.set_title(f"Rent trend: {region_name} [{area_code}]\n{title_metric}")

    fig.subplots_adjust(bottom=0.22, top=0.88)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
