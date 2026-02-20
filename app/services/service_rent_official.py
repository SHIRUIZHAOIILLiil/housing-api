import sqlite3, re
from typing import Optional, List
from app.schemas.rent_stats_official import RentStatsOfficialOut, BedStats, OverallStats, PropertyTypePrices, RentStatsAvailabilityOut

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

def _bed(index, price) -> Optional[BedStats]:
    if index is None and price is None:
        return None
    return BedStats(index=index, rental_price=price)

def validate_yyyy_mm(value: Optional[str], field_name: str) -> None:
    if value is None:
        return
    if not YYYY_MM_RE.match(value):
        raise ValueError(f"Invalid {field_name}. Expected format YYYY-MM.")


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