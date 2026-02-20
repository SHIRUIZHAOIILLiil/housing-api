# app/services/sales_official_service.py

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from app.schemas.sales_official import SalesTransactionsQuery


SALES_TABLE = "sales_transactions_official"
POSTCODE_MAP_TABLE = "postcode_map"
AREAS_TABLE = "areas"

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
        clauses.append("REPLACE(UPPER(st.postcode), ' ', '') LIKE ?")
        params.append(f"%{filters.postcode_like}%")

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


def list_official_sales_transactions(
    conn: sqlite3.Connection,
    filters: SalesTransactionsQuery,
) -> list[dict[str, Any]]:
    """
    GET /official/sales-transactions
    Returns: List (can be empty)
    """
    conn.row_factory = sqlite3.Row

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
    GET /official/sales-transactions/{transaction_uuid}
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
    return _row_to_dict(row) if row else None


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
        return None

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
    GET /official/postcodes/{postcode}/sales-transactions
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
        return None

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