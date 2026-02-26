"""
Service layer for official sales transactions and aggregated statistics.

Responsibilities
- Query and filter HM Land Registry transactions by area_code/postcode/date range and property attributes.
- Provide point stats and series stats aggregated by (area_code, time_period).
- Provide availability helpers (min/max time_period) for stats endpoints.
- Enforce consistent validation and normalization for:
  - transaction_uuid (format/length if needed)
  - postcode normalization
  - time_period formatting (YYYY-MM) and date range logic

Implementation notes
- Keep SQL construction safe: use parameterized queries for user input.
- Centralize optional filter SQL building to reduce duplicated logic and ensure consistent semantics.

Error handling
- Raise NotFoundError when no entity/data exists for the given identifier.
- Raise BadRequestError when period/date ranges are malformed or contradictory.
"""

from __future__ import annotations

import sqlite3, re
from typing import Any, Optional
from app.schemas.sales_official import SalesTransactionsQuery
from app.schemas.errors import BadRequestError, NotFoundError

SALES_TABLE = "sales_transactions_official"
POSTCODE_MAP_TABLE = "postcode_map"
AREAS_TABLE = "areas"

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_yyyymm(value: str, field: str) -> None:
    if not value or not YYYY_MM_RE.match(value):
        raise BadRequestError(f"Invalid {field}. Expected YYYY-MM.")


def _normalize_new_build(v):
    if v is None:
        return None
    return "Y" if int(v) == 1 else "N"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """sqlite3.Row -> dict"""
    d = dict(row)
    d["new_build"] = _normalize_new_build(d.get("new_build"))
    return d


def _build_sales_where(filters: SalesTransactionsQuery) -> tuple[str, list[Any]]:
    """
    Construct the WHERE clause based on filters (parameterized, to prevent SQL injection)
    Returns: (where_sql, params)
    """
    clauses: list[str] = []
    params: list[Any] = []

    # Define as a UUID prefix
    if getattr(filters, "postcode_like", None):
        q = str(filters.postcode_like).strip().upper().replace(" ", "")
        clauses.append("REPLACE(UPPER(st.postcode), ' ', '') LIKE ?")
        params.append(f"%{q}%")

    if getattr(filters, "uuid_prefix", None):
        clauses.append("LOWER(st.transaction_uuid) LIKE ?")
        params.append(f"{filters.uuid_prefix}%")

    if filters.date_from:
        clauses.append("st.transaction_date >= ?")
        params.append(filters.date_from.isoformat())

    if filters.date_to:
        clauses.append("st.transaction_date <= ?")
        params.append(filters.date_to.isoformat())

    if filters.min_price is not None:
        clauses.append("st.price >= ?")
        params.append(filters.min_price)

    if filters.max_price is not None:
        clauses.append("st.price <= ?")
        params.append(filters.max_price)

    if filters.property_type:
        clauses.append("st.property_type = ?")
        params.append(filters.property_type)

    if filters.new_build:
        clauses.append("st.new_build = ?")
        params.append(filters.new_build)

    if filters.tenure:
        clauses.append("st.tenure = ?")
        params.append(filters.tenure)

    if not clauses:
        return "", []

    return " WHERE " + " AND ".join(clauses), params


def _build_order_by(filters: SalesTransactionsQuery) -> str:
    """
        Only allow sorting by whitelisted fields to prevent ORDER BY injection.
    """
    sort_map = {
        "transaction_date": "st.transaction_date",
        "price": "st.price",
    }
    col = sort_map.get(filters.sort_by, "st.transaction_date")
    direction = "ASC" if filters.order == "asc" else "DESC"
    return f" ORDER BY {col} {direction} "


def _build_stats_extra_filters(filters) -> tuple[str, list[Any]]:
    """
    Additional filters for stats (price/type/new_build/tenure)
    Returns (" AND ...", params)
    """
    clauses: list[str] = []
    params: list[Any] = []

    if filters.min_price is not None:
        clauses.append("st.price >= ?")
        params.append(filters.min_price)

    if filters.max_price is not None:
        clauses.append("st.price <= ?")
        params.append(filters.max_price)

    if filters.property_type:
        clauses.append("st.property_type = ?")
        params.append(filters.property_type)

    if filters.new_build is not None:
        clauses.append("st.new_build = ?")
        params.append(1 if filters.new_build else 0)

    if filters.tenure:
        clauses.append("st.tenure = ?")
        params.append(filters.tenure)

    if not clauses:
        return "", []

    return " AND " + " AND ".join(clauses), params


def list_official_sales_transactions(
        conn: sqlite3.Connection,
        filters: SalesTransactionsQuery,
) -> list[dict[str, Any]]:
    """
    GET /official/sales-transactions
    Returns: List (can be empty)
    """
    conn.row_factory = sqlite3.Row

    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise BadRequestError("date_from cannot be after date_to")

    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    where_sql, params = _build_sales_where(filters)
    order_sql = _build_order_by(filters)

    total: Optional[int] = None
    if filters.include_total:
        count_sql = f"""
               SELECT COUNT(*)
               FROM {SALES_TABLE} AS st
               LEFT JOIN {POSTCODE_MAP_TABLE} AS pm
                   ON pm.postcode = st.postcode
               {where_sql}
           """
        total = conn.execute(count_sql, params).fetchone()[0]

    data_sql = f"""
        SELECT
            st.transaction_uuid,
            st.price,
            st.transaction_date,
            st.postcode,
            pm.area_code AS area_code,
            st.property_type,
            st.new_build,
            st.tenure,
            st.paon,
            st.saon
        FROM {SALES_TABLE} AS st
        LEFT JOIN {POSTCODE_MAP_TABLE} AS pm
            ON pm.postcode = st.postcode
        {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
    """

    rows = conn.execute(data_sql, params + [filters.limit, filters.offset]).fetchall()
    items = [_row_to_dict(r) for r in rows]
    return items, total


def get_official_sales_transaction_by_uuid(
        conn: sqlite3.Connection,
        transaction_uuid: str,
) -> Optional[dict[str, Any]]:
    """
    GET sales-transactions/transactions/{transaction_uuid}
    Returns None if not found
    """
    conn.row_factory = sqlite3.Row

    sql = f"""
        SELECT
            st.transaction_uuid,
            st.price,
            st.transaction_date,
            st.postcode,
            pm.area_code AS area_code,
            st.property_type,
            st.new_build,
            st.tenure,
            st.paon,
            st.saon
        FROM {SALES_TABLE} AS st
        LEFT JOIN {POSTCODE_MAP_TABLE} AS pm
            ON pm.postcode = st.postcode
        WHERE st.transaction_uuid = ?
        LIMIT 1
    """
    row = conn.execute(sql, (transaction_uuid,)).fetchone()
    if not row:
        raise NotFoundError("Transaction not found")
    return _row_to_dict(row)


def list_official_sales_transactions_by_area(
        conn: sqlite3.Connection,
        area_code: str,
        filters: SalesTransactionsQuery,
) -> Optional[list[dict[str, Any]]]:
    """
    GET /official/areas/{area_code}/sales-transactions
    - If the area does not exist: Returns None (router -> 404)
    - If the area exists: Returns a list (can be empty)
    """
    conn.row_factory = sqlite3.Row

    # First check if the area exists (to avoid "not found but actually the area_code is wrong")
    exists = conn.execute(
        f"SELECT 1 FROM {AREAS_TABLE} WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    if not exists:
        raise NotFoundError("Area not found")

    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise BadRequestError("date_from cannot be after date_to")

    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    where_sql, params = _build_sales_where(filters)
    order_sql = _build_order_by(filters)

    # area_code is an additional-fixed constraint: concatenated to WHERE (parameterized).
    if where_sql:
        where_sql += " AND pm.area_code = ?"
    else:
        where_sql = " WHERE pm.area_code = ?"
    params = params + [area_code]

    total: Optional[int] = None
    if filters.include_total:
        count_sql = f"""
            SELECT COUNT(*)
            FROM {SALES_TABLE} AS st
            JOIN {POSTCODE_MAP_TABLE} AS pm
                ON pm.postcode = st.postcode
            {where_sql}
        """
        total = conn.execute(count_sql, params).fetchone()[0]

    data_sql = f"""
        SELECT
            st.transaction_uuid,
            st.price,
            st.transaction_date,
            st.postcode,
            pm.area_code AS area_code,
            st.property_type,
            st.new_build,
            st.tenure,
            st.paon,
            st.saon
        FROM {SALES_TABLE} AS st
        JOIN {POSTCODE_MAP_TABLE} AS pm
            ON pm.postcode = st.postcode
        {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
    """

    rows = conn.execute(data_sql, params + [filters.limit, filters.offset]).fetchall()
    items = [_row_to_dict(r) for r in rows]
    return items, total


def list_official_sales_transactions_by_postcode(
        conn: sqlite3.Connection,
        postcode: str,
        filters: SalesTransactionsQuery,
) -> Optional[list[dict[str, Any]]]:
    """
    GET /postcodes/{postcode}/sales-transactions
    - If postcode does not exist: Returns None (router -> 404)
    - If postcode exists: Returns a list (can be empty)
    """
    conn.row_factory = sqlite3.Row

    pc_norm = postcode.strip().upper().replace(" ", "")

    # Check if postcode exists (in postcode_map)
    exists = conn.execute(
        f"SELECT 1 FROM {POSTCODE_MAP_TABLE} WHERE postcode = ? LIMIT 1",
        (pc_norm,),
    ).fetchone()
    if not exists:
        raise NotFoundError("Postcode not found")

    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise BadRequestError("date_from cannot be after date_to")

    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    where_sql, params = _build_sales_where(filters)
    order_sql = _build_order_by(filters)

    # Fixed constraint: st.postcode = ?
    if where_sql:
        where_sql += " AND st.postcode = ?"
    else:
        where_sql = " WHERE st.postcode = ?"
    params = params + [pc_norm]

    total: Optional[int] = None
    if filters.include_total:
        count_sql = f"""
            SELECT COUNT(*)
            FROM {SALES_TABLE} AS st
            LEFT JOIN {POSTCODE_MAP_TABLE} AS pm
                ON pm.postcode = st.postcode
            {where_sql}
        """
        total = conn.execute(count_sql, params).fetchone()[0]

    data_sql = f"""
            SELECT
                st.transaction_uuid,
                st.price,
                st.transaction_date,
                st.postcode,
                pm.area_code AS area_code,
                st.property_type,
                st.new_build,
                st.tenure,
                st.paon,
                st.saon
            FROM {SALES_TABLE} AS st
            LEFT JOIN {POSTCODE_MAP_TABLE} AS pm
                ON pm.postcode = st.postcode
            {where_sql}
            {order_sql}
            LIMIT ? OFFSET ?
        """

    rows = conn.execute(data_sql, params + [filters.limit, filters.offset]).fetchall()
    items = [_row_to_dict(r) for r in rows]
    return items, total


def get_official_sales_stats_point(
        conn: sqlite3.Connection,
        area_code: str,
        time_period: str,
        filters,
) -> Optional[dict[str, Any]]:
    """
    Point stats: (area_code, time_period) -> aggregated result
    """
    conn.row_factory = sqlite3.Row

    exists = conn.execute(
        f"SELECT 1 FROM areas WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    _validate_yyyymm(time_period, "time_period")

    if not exists:
        raise NotFoundError("Area not found")  # router -> 404 area not found

    extra_sql, extra_params = _build_stats_extra_filters(filters)

    sql = f"""
        SELECT
            pm.area_code AS area_code,
            SUBSTR(st.transaction_date, 1, 7) AS time_period,
            COUNT(*) AS count,
            AVG(st.price) AS avg_price,
            MIN(st.price) AS min_price,
            MAX(st.price) AS max_price,
            SUM(st.price) AS total_value
        FROM sales_transactions_official AS st
        JOIN postcode_map AS pm
            ON pm.postcode = st.postcode
        WHERE pm.area_code = ?
          AND SUBSTR(st.transaction_date, 1, 7) = ?
          {extra_sql}
        GROUP BY pm.area_code, SUBSTR(st.transaction_date, 1, 7)
        LIMIT 1
    """

    row = conn.execute(sql, [area_code, time_period] + extra_params).fetchone()
    if not row:
        raise NotFoundError("No data available")
    return dict(row)  # {} indicates that the area exists but there is no data for that month.


def list_official_sales_stats_series(
        conn: sqlite3.Connection,
        area_code: str,
        filters,
) -> Optional[tuple[list[dict[str, Any]], Optional[int]]]:
    """
    Series stats by month for an area_code.
    - area not exist -> None
    - exist -> list (may be empty)
    """
    conn.row_factory = sqlite3.Row

    if filters.from_period and filters.to_period and filters.from_period > filters.to_period:
        raise BadRequestError("from_period cannot be after to_period")

    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    exists = conn.execute(
        f"SELECT 1 FROM areas WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    if not exists:
        raise NotFoundError("Area not found")

    where = ["pm.area_code = ?"]
    params: list[Any] = [area_code]

    if filters.from_period:
        where.append("SUBSTR(st.transaction_date, 1, 7) >= ?")
        params.append(filters.from_period)

    if filters.to_period:
        where.append("SUBSTR(st.transaction_date, 1, 7) <= ?")
        params.append(filters.to_period)

    extra_sql, extra_params = _build_stats_extra_filters(filters)
    params += extra_params

    where_sql = " WHERE " + " AND ".join(where) + extra_sql

    total: Optional[int] = None

    sql = f"""
        SELECT
            SUBSTR(st.transaction_date, 1, 7) AS time_period,
            COUNT(*) AS count,
            AVG(st.price) AS avg_price,
            MIN(st.price) AS min_price,
            MAX(st.price) AS max_price,
            SUM(st.price) AS total_value
        FROM sales_transactions_official AS st
        JOIN postcode_map AS pm
            ON pm.postcode = st.postcode
        {where_sql}
        GROUP BY SUBSTR(st.transaction_date, 1, 7)
        ORDER BY time_period ASC
        LIMIT ? OFFSET ?
    """

    rows = conn.execute(sql, params + [filters.limit, filters.offset]).fetchall()
    return [dict(r) for r in rows], total


def get_official_sales_stats_availability(
        conn: sqlite3.Connection,
        area_code: str,
) -> Optional[dict[str, Any]]:
    conn.row_factory = sqlite3.Row

    exists = conn.execute(
        f"SELECT 1 FROM areas WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    if not exists:
        raise NotFoundError("Area not found")

    sql = f"""
        SELECT
            MIN(SUBSTR(st.transaction_date, 1, 7)) AS min_time_period,
            MAX(SUBSTR(st.transaction_date, 1, 7)) AS max_time_period,
            COUNT(DISTINCT SUBSTR(st.transaction_date, 1, 7)) AS months
        FROM sales_transactions_official AS st
        JOIN postcode_map AS pm
            ON pm.postcode = st.postcode
        WHERE pm.area_code = ?
    """
    row = conn.execute(sql, (area_code,)).fetchone()
    return {"area_code": area_code, **dict(row)}


def get_official_sales_stats_latest(
        conn: sqlite3.Connection,
        area_code: str,
        filters,
) -> Optional[dict[str, Any]]:
    conn.row_factory = sqlite3.Row

    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    exists = conn.execute(
        f"SELECT 1 FROM areas WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    if not exists:
        raise NotFoundError("Area not found")

    extra_sql, extra_params = _build_stats_extra_filters(filters)

    # Find the latest month for this area (under filters).
    sql_latest = f"""
        SELECT
            MAX(SUBSTR(st.transaction_date, 1, 7)) AS latest_period
        FROM sales_transactions_official st
        JOIN postcode_map AS pm
            ON pm.postcode = st.postcode
        WHERE pm.area_code = ?
        {extra_sql}
    """
    row = conn.execute(sql_latest, [area_code] + extra_params).fetchone()
    latest_period = row["latest_period"] if row else None
    if not latest_period:
        raise NotFoundError("No data available")  # The area exists but no transactions have been completed.

    return get_official_sales_stats_point(conn, area_code, latest_period, filters)
