"""
User-generated rental record endpoints.

This router provides full CRUD operations for rental records created by users.
It is intentionally separate from official rent statistics to avoid contaminating reference datasets.

Endpoints
- POST /rent_user
  Create a new user rental record.
- GET /rent_user
  List user rental records with filtering and pagination.
- GET /rent_user/{record_id}
  Retrieve a specific user rental record.
- PUT /rent_user/{record_id}
  Replace a user rental record (full update).
- PATCH /rent_user/{record_id}
  Partially update a user rental record.
- DELETE /rent_user/{record_id}
  Delete a user rental record.

Notes
- postcode/area_code should be consistent with postcode_map and areas tables (FK constraints).
- If area_code is optional in the schema, the service may derive it from postcode_map.
- Unknown record_id raises NotFoundError (404).
- Validation errors are returned as 422; domain errors (e.g., inconsistent FK) are returned as 400/404 depending on your global mapping.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status, Query, Request
import sqlite3
from typing import Optional

from app.api.deps import get_conn, COMMON_ERROR_RESPONSES, get_current_user
from app.schemas import (
    RentalRecordCreate,
    RentalRecordUpdate,
    RentalRecordOut,
    RentalRecordListOut,
    RentalRecordPatch,
    UserOut
)
from app.services.service_rent_user import (
    create_rental_record,
    get_rental_record,
    list_rental_records,
    update_rental_record,
    delete_rental_record,
    patch_rental_record
)

router = APIRouter()


@router.post(
    "",
    response_model=RentalRecordOut,
    status_code=status.HTTP_201_CREATED,
    responses=COMMON_ERROR_RESPONSES,

)
def api_create_rental_record(payload: RentalRecordCreate,
                             request: Request,
                             conn: sqlite3.Connection = Depends(get_conn),
                             user: UserOut = Depends(get_current_user),
                             ):
    request_id = getattr(request.state, "request_id", None)
    return create_rental_record(conn, payload, user, request_id)


@router.get(
    "/{record_id}",
    response_model=RentalRecordOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_get_rental_record(record_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    return get_rental_record(conn, record_id)


@router.get(
    "",
    response_model=RentalRecordListOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_list_rental_records(
    time_period: Optional[str] = None,
    area_code: Optional[str] = None,
    postcode: Optional[str] = None,
    bedrooms: Optional[int] = None,
    property_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
):
    items = list_rental_records(
        conn,
        time_period=time_period,
        area_code=area_code,
        postcode=postcode,
        bedrooms=bedrooms,
        property_type=property_type,
        limit=limit,
        offset=offset,
    )
    return RentalRecordListOut(items=items)


@router.put(
    "/{record_id}",
    response_model=RentalRecordOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_update_rental_record(
    record_id: int,
    request: Request,
    patch: RentalRecordUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    user: UserOut = Depends(get_current_user)
):
    request_id = getattr(request.state, "request_id", None)
    return update_rental_record(conn, record_id, patch, user, request_id)


@router.patch(
    "/{record_id}",
    response_model=RentalRecordOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_patch_rental_record(
    record_id: int,
    request: Request,
    patch: RentalRecordPatch,
    conn: sqlite3.Connection = Depends(get_conn),
    user: UserOut = Depends(get_current_user)
):
    request_id = getattr(request.state, "request_id", None)
    return patch_rental_record(conn, record_id, patch, user, request_id)

@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON_ERROR_RESPONSES
)
def api_delete_rental_record(record_id: int,
                             request: Request,
                             conn: sqlite3.Connection = Depends(get_conn),
                             user: UserOut = Depends(get_current_user)):
    request_id = getattr(request.state, "request_id", None)
    delete_rental_record(conn, record_id, user, request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
