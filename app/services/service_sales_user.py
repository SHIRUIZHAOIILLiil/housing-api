"""
Service layer for user sales transactions.

Responsibilities
- Implement CRUD operations over the user sales table.
- Apply optional filters in list endpoints:
  - postcode, area_code
  - from_period/to_period (YYYY-MM range)
  - property_type
  - min_price/max_price
- Enforce domain-level validation:
  - price must be positive
  - time_period format and range logic
  - FK existence checks if your design requires pre-validation (in addition to DB constraints)

Implementation notes
- Centralize dynamic WHERE clause construction to keep filter semantics consistent.
- Ensure list endpoints have deterministic ordering if tests rely on stable pagination.

Error handling
- Raise NotFoundError when record_id does not exist.
- Raise BadRequestError for malformed or contradictory filters (e.g., min_price > max_price).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.schemas.schema_sales_user import (
    SalesUserCreate,
    SalesUserPatch,
    SalesUserOut,
    YYYY_MM_RE,
)
from app.schemas.errors import BadRequestError, NotFoundError
from app.schemas import UserOut
from app.services.service_audit import log_audit_event

def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def norm_postcode(pc: str) -> str:
    pc = (pc or "").strip().upper().replace(" ", "")
    return pc


def _validate_time_period(tp: str) -> None:
    if not YYYY_MM_RE.match(tp):
        raise BadRequestError("Invalid time_period format. Expected YYYY-MM (e.g. 2024-07).")


def _ensure_postcode_exists(conn: sqlite3.Connection, postcode: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM postcode_map WHERE postcode = ? LIMIT 1",
        (postcode,),
    ).fetchone()
    if row is None:
        raise NotFoundError("postcode not found")


def _ensure_area_exists(conn: sqlite3.Connection, area_code: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM areas WHERE area_code = ? LIMIT 1",
        (area_code,),
    ).fetchone()
    if row is None:
        raise NotFoundError("area_code not found")


def _derive_area_code(conn: sqlite3.Connection, postcode: str) -> str:
    """
    Assumes postcode_map has (postcode, area_code).
    If your column name differs, tell me and I’ll adjust.
    """
    row = conn.execute(
        "SELECT area_code FROM postcode_map WHERE postcode = ? LIMIT 1",
        (postcode,),
    ).fetchone()
    if row is None or row["area_code"] is None:
        raise NotFoundError("postcode not found")
    return row["area_code"]


def _ensure_postcode_area_consistent(conn: sqlite3.Connection, postcode: str, area_code: str) -> None:
    mapped = _derive_area_code(conn, postcode)
    if mapped != area_code:
        raise BadRequestError("postcode and area_code mismatch for postcode_map.")


def create_user_sale(conn: sqlite3.Connection, payload: SalesUserCreate, user: UserOut, request_id=None) -> SalesUserOut:
    user_id = user.id
    postcode = norm_postcode(payload.postcode)
    if not postcode:
        raise BadRequestError("postcode cannot be empty")

    time_period = payload.time_period.strip()
    _validate_time_period(time_period)

    _ensure_postcode_exists(conn, postcode)

    # area_code: can be omitted → deduced from postcode_map
    if payload.area_code is None or payload.area_code.strip() == "":
        area_code = _derive_area_code(conn, postcode)
    else:
        area_code = payload.area_code.strip()
        _ensure_area_exists(conn, area_code)
        _ensure_postcode_area_consistent(conn, postcode, area_code)

    # Basic price verification has been done by Pydantic (gt=0)
    price = float(payload.price)

    created_at = _utc_now_str()
    source = payload.source

    cur = conn.execute(
        """
        INSERT INTO sales_transactions_user
        (postcode, area_code, time_period, price, property_type, created_at, source, uploader_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            postcode,
            area_code,
            time_period,
            price,
            payload.property_type,
            created_at,
            source,
            user_id,
        ),
    )

    new_id = int(cur.lastrowid)

    log_audit_event(
        conn=conn,
        user_id=user.id,
        action="CREATE",
        resource_type="sales_transactions_user",
        resource_id=new_id,
        request_id=request_id,
        detail={
            "after": {
                "postcode": postcode,
                "area_code": area_code,
                "time_period": time_period,
                "price": price,
                "property_type": payload.property_type,
                "source": source,
            }
        },
    )

    conn.commit()
    return get_user_sale(conn, new_id)


def get_user_sale(conn: sqlite3.Connection, record_id: int, ) -> SalesUserOut:
    row = conn.execute(
        """
        SELECT id, postcode, area_code, time_period, price, property_type, created_at, source
        FROM sales_transactions_user
        WHERE id = ?
        """,
        (record_id,),
    ).fetchone()

    if row is None:
        raise NotFoundError("transaction not found")

    return SalesUserOut(
        id=row["id"],
        postcode=row["postcode"],
        area_code=row["area_code"],
        time_period=row["time_period"],
        price=row["price"],
        property_type=row["property_type"],
        created_at=row["created_at"],
        source=row["source"],
    )


def list_user_sales(
    conn: sqlite3.Connection,
    postcode: Optional[str] = None,
    area_code: Optional[str] = None,
    from_period: Optional[str] = None,
    to_period: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SalesUserOut]:
    where = []
    params: list[object] = []

    if postcode:
        where.append("postcode = ?")
        params.append(norm_postcode(postcode))

    if area_code:
        where.append("area_code = ?")
        params.append(area_code.strip())

    if from_period:
        fp = from_period.strip()
        _validate_time_period(fp)
        where.append("time_period >= ?")
        params.append(fp)

    if to_period:
        tp = to_period.strip()
        _validate_time_period(tp)
        where.append("time_period <= ?")
        params.append(tp)

    if property_type:
        where.append("property_type = ?")
        params.append(property_type.strip())

    if min_price is not None:
        where.append("price >= ?")
        params.append(float(min_price))

    if max_price is not None:
        where.append("price <= ?")
        params.append(float(max_price))

    sql = """
        SELECT id, postcode, area_code, time_period, price, property_type, created_at, source
        FROM sales_transactions_user
    """

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    rows = conn.execute(sql, tuple(params)).fetchall()

    return [
        SalesUserOut(
            id=r["id"],
            postcode=r["postcode"],
            area_code=r["area_code"],
            time_period=r["time_period"],
            price=r["price"],
            property_type=r["property_type"],
            created_at=r["created_at"],
            source=r["source"],
        )
        for r in rows
    ]

def replace_user_sale(conn: sqlite3.Connection, record_id: int, payload: SalesUserCreate, user: UserOut, request_id=None) -> SalesUserOut:
    """
    PUT semantics: replace the whole resource (except server-managed created_at).
    We keep created_at unchanged.
    """
    current = get_user_sale(conn, record_id)
    before = current.model_dump()

    postcode = norm_postcode(payload.postcode)
    if not postcode:
        raise BadRequestError("postcode cannot be empty")

    time_period = payload.time_period.strip()
    _validate_time_period(time_period)

    _ensure_postcode_exists(conn, postcode)

    if payload.area_code is None or payload.area_code.strip() == "":
        area_code = _derive_area_code(conn, postcode)
    else:
        area_code = payload.area_code.strip()
        _ensure_area_exists(conn, area_code)
        _ensure_postcode_area_consistent(conn, postcode, area_code)

    price = float(payload.price)

    source = payload.source

    conn.execute(
        """
        UPDATE sales_transactions_user
        SET postcode = ?,
            area_code = ?,
            time_period = ?,
            price = ?,
            property_type = ?,
            source = ?
        WHERE id = ?
        """,
        (
            postcode,
            area_code,
            time_period,
            price,
            payload.property_type,
            source,
            record_id,
        ),
    )

    after = get_user_sale(conn, record_id)

    log_audit_event(
        conn=conn,
        user_id=user.id,
        action="UPDATE",
        resource_type="sales_transactions_user",
        resource_id=record_id,
        request_id=request_id,
        detail={
            "before": before,
            "after": after.model_dump(),
        },
    )

    conn.commit()

    return after

def patch_user_sale(conn: sqlite3.Connection, record_id: int, patch: SalesUserPatch, user: UserOut, request_id=None) -> SalesUserOut:
    # Confirmed to exist
    current = get_user_sale(conn, record_id)
    before = current.model_dump()

    fields = []
    params: list[object] = []

    if patch.time_period is not None:
        tp = patch.time_period.strip()
        _validate_time_period(tp)
        fields.append("time_period = ?")
        params.append(tp)

    if patch.price is not None:
        fields.append("price = ?")
        params.append(float(patch.price))

    if patch.property_type is not None:
        fields.append("property_type = ?")
        params.append(patch.property_type)

    if not fields:
        raise BadRequestError("No fields provided for update.")

    params.append(record_id)
    conn.execute(
        f"UPDATE sales_transactions_user SET {', '.join(fields)} WHERE id = ?",
        tuple(params),
    )
    after = get_user_sale(conn, record_id)
    log_audit_event(
        conn=conn,
        user_id=user.id,
        action="UPDATE",
        resource_type="sales_transactions_user",
        resource_id=record_id,
        request_id=request_id,
        detail={
            "before": before,
            "after": after.model_dump(),
        },
    )

    conn.commit()

    return after


def delete_user_sale(conn: sqlite3.Connection, record_id: int, user: UserOut, request_id=None) -> None:
    current = get_user_sale(conn, record_id)
    before = current.model_dump()

    conn.execute("DELETE FROM sales_transactions_user WHERE id = ?", (record_id,))

    log_audit_event(
        conn=conn,
        user_id=user.id,
        action="DELETE",
        resource_type="sales_transactions_user",
        resource_id=record_id,
        request_id=request_id,
        detail={
            "before": before,
        },
    )

    conn.commit()
