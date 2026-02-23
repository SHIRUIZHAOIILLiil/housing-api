# app/services/rent_user_service.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional
from fastapi import Query

from app.schemas.schema_rent_user import (
    RentalRecordCreate,
    RentalRecordUpdate,
    RentalRecordOut,
    YYYY_MM_RE,
    RentalRecordPatch
)
from app.schemas.errors import NotFoundError, BadRequestError

def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def norm_postcode(pc: str) -> str:
    """
    Minimal postcode normalizer:
    - strip
    - uppercase
    - collapse whitespace to single space
    """
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

def _ensure_postcode_area_consistent(conn: sqlite3.Connection, postcode: str, area_code: str) -> None:
    mapped = _derive_area_code(conn, postcode)
    if mapped != area_code:
        raise BadRequestError("postcode and area_code mismatch for postcode_map.")


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


def create_rental_record(conn: sqlite3.Connection, payload: RentalRecordCreate) -> RentalRecordOut:
    postcode = norm_postcode(payload.postcode)
    if not postcode:
        raise BadRequestError("postcode cannot be empty")
    _ensure_postcode_exists(conn, postcode)

    time_period = payload.time_period.strip()
    _validate_time_period(time_period)

    area_code_in = (payload.area_code or "").strip()
    if area_code_in == "":
        area_code = _derive_area_code(conn, postcode)
    else:
        _ensure_area_exists(conn, area_code_in)
        _ensure_postcode_area_consistent(conn, postcode, area_code_in)
        area_code = area_code_in

    created_at = _utc_now_str()
    source = payload.source

    cur = conn.execute(
        """
        INSERT INTO rent_stats_user
        (postcode, area_code, time_period, rent, bedrooms, property_type, created_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            postcode,
            area_code,
            time_period,
            float(payload.rent),
            payload.bedrooms,
            payload.property_type,
            created_at,
            source,
        ),
    )
    conn.commit()

    new_id = cur.lastrowid
    return get_rental_record(conn, new_id)


def get_rental_record(conn: sqlite3.Connection, record_id: int) -> RentalRecordOut:
    row = conn.execute(
        """
        SELECT id, postcode, area_code, time_period, rent, bedrooms, property_type, created_at, source
        FROM rent_stats_user
        WHERE id = ?
        """,
        (record_id,),
    ).fetchone()

    if row is None:
        raise NotFoundError("record not found")

    return RentalRecordOut(
        id=row["id"],
        postcode=row["postcode"],
        area_code=row["area_code"],
        time_period=row["time_period"],
        rent=row["rent"],
        bedrooms=row["bedrooms"],
        property_type=row["property_type"],
        created_at=row["created_at"],
        source=row["source"],
    )


def list_rental_records(
    conn: sqlite3.Connection,
    time_period: Optional[str] = None,
    area_code: Optional[str] = None,
    postcode: Optional[str] = None,
    bedrooms: Optional[int] = None,
    property_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[RentalRecordOut]:
    where = []
    params: list[object] = []

    if time_period:
        time_period = time_period.strip()
        _validate_time_period(time_period)
        where.append("time_period = ?")
        params.append(time_period)

    if area_code:
        where.append("area_code = ?")
        params.append(area_code.strip())

    if postcode:
        where.append("postcode = ?")
        params.append(norm_postcode(postcode))

    if bedrooms is not None:
        where.append("bedrooms = ?")
        params.append(int(bedrooms))

    if property_type:
        where.append("property_type = ?")
        params.append(property_type.strip())

    sql = """
        SELECT id, postcode, area_code, time_period, rent, bedrooms, property_type, created_at, source
        FROM rent_stats_user
    """

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        RentalRecordOut(
            id=r["id"],
            postcode=r["postcode"],
            area_code=r["area_code"],
            time_period=r["time_period"],
            rent=r["rent"],
            bedrooms=r["bedrooms"],
            property_type=r["property_type"],
            created_at=r["created_at"],
            source=r["source"],
        )
        for r in rows
    ]

def _validate_update_consistency(conn: sqlite3.Connection, new_postcode: str, new_area_code: str) -> None:
    _ensure_postcode_exists(conn, new_postcode)
    _ensure_area_exists(conn, new_area_code)
    _ensure_postcode_area_consistent(conn, new_postcode, new_area_code)

def update_rental_record(conn: sqlite3.Connection, record_id: int, patch: RentalRecordUpdate) -> RentalRecordOut:
    current = get_rental_record(conn, record_id)

    fields = []
    params: list[object] = []

    final_postcode = current.postcode
    final_area_code = current.area_code

    if patch.postcode is not None:
        pc = norm_postcode(patch.postcode)
        _ensure_postcode_exists(conn, pc)
        fields.append("postcode = ?")
        params.append(pc)

    if patch.area_code is not None:
        ac = patch.area_code.strip()
        _ensure_area_exists(conn, ac)
        fields.append("area_code = ?")
        params.append(ac)

    if patch.postcode is not None or patch.area_code is not None:
        _validate_update_consistency(conn, final_postcode, final_area_code)

    if patch.time_period is not None:
        tp = patch.time_period.strip()
        _validate_time_period(tp)
        fields.append("time_period = ?")
        params.append(tp)

    if patch.rent is not None:
        fields.append("rent = ?")
        params.append(float(patch.rent))

    if patch.bedrooms is not None:
        fields.append("bedrooms = ?")
        params.append(int(patch.bedrooms))

    if patch.property_type is not None:
        fields.append("property_type = ?")
        params.append(patch.property_type)

    if patch.source is not None:
        fields.append("source = ?")
        params.append(patch.source)

    if not fields:
        raise BadRequestError("No fields provided for update.")

    params.append(record_id)
    conn.execute(
        f"UPDATE rent_stats_user SET {', '.join(fields)} WHERE id = ?",
        tuple(params),
    )
    conn.commit()

    return get_rental_record(conn, record_id)


def delete_rental_record(conn: sqlite3.Connection, record_id: int) -> None:
    _ = get_rental_record(conn, record_id)

    conn.execute("DELETE FROM rent_stats_user WHERE id = ?", (record_id,))
    conn.commit()

def patch_rental_record(conn: sqlite3.Connection, record_id: int, patch: RentalRecordPatch) -> RentalRecordOut:
    # First, confirm its existence (if it doesn't exist, return 404).
    current = get_rental_record(conn, record_id)

    fields = []
    params: list[object] = []

    final_postcode = current.postcode
    final_area_code = current.area_code

    if patch.postcode is not None:
        pc = norm_postcode(patch.postcode)
        _ensure_postcode_exists(conn, pc)
        fields.append("postcode = ?")
        params.append(pc)

    if patch.area_code is not None:
        ac = patch.area_code.strip()
        _ensure_area_exists(conn, ac)
        fields.append("area_code = ?")
        params.append(ac)

    if patch.postcode is not None or patch.area_code is not None:
        _validate_update_consistency(conn, final_postcode, final_area_code)

    if patch.time_period is not None:
        tp = patch.time_period.strip()
        _validate_time_period(tp)
        fields.append("time_period = ?")
        params.append(tp)

    if patch.rent is not None:
        fields.append("rent = ?")
        params.append(float(patch.rent))

    if patch.bedrooms is not None:
        fields.append("bedrooms = ?")
        params.append(int(patch.bedrooms))

    if patch.property_type is not None:
        fields.append("property_type = ?")
        params.append(patch.property_type)

    if patch.source is not None:
        fields.append("source = ?")
        params.append(patch.source)

    if not fields:
        raise BadRequestError("No fields provided for update.")

    params.append(record_id)

    conn.execute(
        f"UPDATE rent_stats_user SET {', '.join(fields)} WHERE id = ?",
        tuple(params),
    )
    conn.commit()

    return get_rental_record(conn, record_id)