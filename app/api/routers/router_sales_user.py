from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Response, status, Query

from app.api.deps import get_conn, COMMON_ERROR_RESPONSES
from app.schemas.schema_sales_user import (
    SalesUserCreate,
    SalesUserOut,
    SalesUserListOut,
    SalesUserPatch,
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
    responses=COMMON_ERROR_RESPONSES
)
def api_create_user_sale(payload: SalesUserCreate, conn: sqlite3.Connection = Depends(get_conn)):
    return create_user_sale(conn, payload)


@router.get(
    "/{record_id}",
    response_model=SalesUserOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_get_user_sale(record_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    return get_user_sale(conn, record_id)


@router.get(
    "",
    response_model=SalesUserListOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_list_user_sales(
    postcode: Optional[str] = None,
    area_code: Optional[str] = None,
    from_period: Optional[str] = None,
    to_period: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
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
        offset=offset,
    )
    return SalesUserListOut(items=items)

@router.put(
    "/{record_id}",
    response_model=SalesUserOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_put_user_sale(
    record_id: int,
    payload: SalesUserCreate,
    conn: sqlite3.Connection = Depends(get_conn),
):
    return replace_user_sale(conn, record_id, payload)


@router.patch(
    "/{record_id}",
    response_model=SalesUserOut,
    responses=COMMON_ERROR_RESPONSES
)
def api_patch_user_sale(
    record_id: int,
    patch: SalesUserPatch,
    conn: sqlite3.Connection = Depends(get_conn),
):
    return patch_user_sale(conn, record_id, patch)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON_ERROR_RESPONSES
)
def api_delete_user_sale(record_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    delete_user_sale(conn, record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
