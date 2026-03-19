"""
User-generated sales transaction endpoints.

This router provides full CRUD operations for user-supplied sales transactions.
It is separate from official HM Land Registry data and is intended for sandboxing user contributions.

Endpoints
- POST /user-sales-transactions
  Create a user sales transaction.
- GET /user-sales-transactions
  List user sales transactions with filtering and pagination.
- GET /user-sales-transactions/{record_id}
  Retrieve a specific user sales transaction.
- PUT /user-sales-transactions/{record_id}
  Replace a user sales transaction (full update).
- PATCH /user-sales-transactions/{record_id}
  Partially update a user sales transaction.
- DELETE /user-sales-transactions/{record_id}
  Delete a user sales transaction.

Notes
- postcode/area_code should be consistent with postcode_map and areas tables (FK constraints).
- If area_code is optional, the service may derive it from postcode_map.
- Unknown record_id raises NotFoundError (404).
- Validation errors are returned as 422; domain errors are mapped consistently via global exception handlers.
"""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Response, status, Query, Request, Path

from app.api.deps import get_conn, AUTH_ERROR_RESPONSES, COMMON_ERROR_RESPONSES, get_current_user
from app.schemas import (
    SalesUserCreate,
    SalesUserOut,
    SalesUserListOut,
    SalesUserPatch,
    UserOut,
)
from app.services.service_sales_user import (
    create_user_sale,
    get_user_sale,
    list_user_sales,
    patch_user_sale,
    delete_user_sale,
    replace_user_sale,
)

router = APIRouter()


@router.post(
    "",
    response_model=SalesUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user sales record",
    description="Create a new user-contributed sales transaction. Requires bearer authentication.",
    responses=AUTH_ERROR_RESPONSES
)
def api_create_user_sale(payload: SalesUserCreate, request: Request, conn: sqlite3.Connection = Depends(get_conn), user: UserOut = Depends(get_current_user)):
    request_id = getattr(request.state, "request_id", None)
    return create_user_sale(conn, payload, user, request_id)


@router.get(
    "/{record_id}",
    response_model=SalesUserOut,
    summary="Get one user sales record",
    description="Return a single user-contributed sales record by its numeric record_id.",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_user_sale(
    record_id: int = Path(..., description="Numeric id of the user sales record.", examples=[7]),
    conn: sqlite3.Connection = Depends(get_conn),
):
    return get_user_sale(conn, record_id)


@router.get(
    "",
    response_model=SalesUserListOut,
    summary="List user sales records",
    description="List user-contributed sales transactions with optional filters and pagination.",
    responses=COMMON_ERROR_RESPONSES
)
def api_list_user_sales(
    postcode: Optional[str] = Query(default=None, description="Filter by postcode.", examples=["LS29JT"]),
    area_code: Optional[str] = Query(default=None, description="Filter by administrative area code.", examples=["E08000035"]),
    from_period: Optional[str] = Query(default=None, description="Filter from month in YYYY-MM format.", examples=["2025-01"]),
    to_period: Optional[str] = Query(default=None, description="Filter to month in YYYY-MM format.", examples=["2025-12"]),
    property_type: Optional[str] = Query(default=None, description="Filter by property type.", examples=["semidetached"]),
    min_price: Optional[float] = Query(default=None, description="Minimum price filter.", examples=[100000]),
    max_price: Optional[float] = Query(default=None, description="Maximum price filter.", examples=[500000]),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of rows to return.", examples=[50]),
    offset: int = Query(default=0, ge=0, description="Number of rows to skip before returning results.", examples=[0]),
    conn: sqlite3.Connection = Depends(get_conn),
):
    items = list_user_sales(
        conn,
        postcode=postcode,
        area_code=area_code,
        from_period=from_period,
        to_period=to_period,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset
    )
    return SalesUserListOut(items=items)

@router.put(
    "/{record_id}",
    response_model=SalesUserOut,
    summary="Replace a user sales record",
    description="Fully replace an existing user-contributed sales record. Requires bearer authentication.",
    responses=AUTH_ERROR_RESPONSES
)
def api_put_user_sale(
    request: Request,
    payload: SalesUserCreate,
    record_id: int = Path(..., description="Numeric id of the user sales record.", examples=[7]),
    conn: sqlite3.Connection = Depends(get_conn),
    user: UserOut = Depends(get_current_user)
):
    request_id = getattr(request.state, "request_id", None)
    return replace_user_sale(conn, record_id, payload, user, request_id)


@router.patch(
    "/{record_id}",
    response_model=SalesUserOut,
    summary="Patch a user sales record",
    description="Partially update an existing user-contributed sales record. Requires bearer authentication.",
    responses=AUTH_ERROR_RESPONSES
)
def api_patch_user_sale(
    request: Request,
    patch: SalesUserPatch,
    record_id: int = Path(..., description="Numeric id of the user sales record.", examples=[7]),
    conn: sqlite3.Connection = Depends(get_conn),
    user: UserOut = Depends(get_current_user)
):
    request_id = getattr(request.state, "request_id", None)
    return patch_user_sale(conn, record_id, patch, user, request_id)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user sales record",
    description="Delete an existing user-contributed sales record. Requires bearer authentication.",
    responses=AUTH_ERROR_RESPONSES
)
def api_delete_user_sale(
    request: Request,
    record_id: int = Path(..., description="Numeric id of the user sales record.", examples=[7]),
    conn: sqlite3.Connection = Depends(get_conn),
    user: UserOut = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", None)
    delete_user_sale(conn, record_id, user, request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
