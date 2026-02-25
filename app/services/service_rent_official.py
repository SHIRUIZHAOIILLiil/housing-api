import matplotlib
matplotlib.use("Agg")
import sqlite3, re, io, matplotlib.pyplot as plt
from typing import Optional, List, Literal
from app.schemas.rent_stats_official import RentStatsOfficialOut, BedStats, OverallStats, PropertyTypePrices, RentStatsAvailabilityOut
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
