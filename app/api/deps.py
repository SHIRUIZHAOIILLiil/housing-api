import sqlite3
from typing import Generator, Optional
from fastapi import Query
from datetime import date
from app.core.config import Settings
from app.schemas.sales_official import (
    SalesGlobalFilters, SalesScopedFilters, PropertyType, NewBuildFlag, TenureType, SortBy, SortOrder
)
from app.schemas.errors import ErrorOut

settings = Settings()

COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorOut, "description": "Invalid input."},
    404: {"model": ErrorOut, "description": "Resource not found."},
}

def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_sales_global_filters(
    postcode_like: Optional[str] = Query(default=None, description="Fuzzy postcode (ignores spaces)"),
    uuid_prefix: Optional[str] = Query(default=None, min_length=4, max_length=64, description="UUID prefix"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    min_price: Optional[int] = Query(default=None, ge=0),
    max_price: Optional[int] = Query(default=None, ge=0),
    property_type: Optional[PropertyType] = Query(default=None),
    new_build: Optional[NewBuildFlag] = Query(default=None),
    tenure: Optional[TenureType] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: SortBy = Query(default="transaction_date"),
    order: SortOrder = Query(default="desc"),
    include_total: bool = Query(default=False),
) -> SalesGlobalFilters:
    if postcode_like:
        postcode_like = postcode_like.strip().upper().replace(" ", "")
    if uuid_prefix:
        uuid_prefix = uuid_prefix.strip().lower()
    return SalesGlobalFilters(
        postcode_like=postcode_like,
        uuid_prefix=uuid_prefix,
        date_from=date_from,
        date_to=date_to,
        min_price=min_price,
        max_price=max_price,
        property_type=property_type,
        new_build=new_build,
        tenure=tenure,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        include_total=include_total,
    )

def get_sales_scoped_filters(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    min_price: Optional[int] = Query(default=None, ge=0),
    max_price: Optional[int] = Query(default=None, ge=0),
    property_type: Optional[PropertyType] = Query(default=None),
    new_build: Optional[NewBuildFlag] = Query(default=None),
    tenure: Optional[TenureType] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: SortBy = Query(default="transaction_date"),
    order: SortOrder = Query(default="desc"),
    include_total: bool = Query(default=False),
) -> SalesScopedFilters:
    return SalesScopedFilters(
        date_from=date_from,
        date_to=date_to,
        min_price=min_price,
        max_price=max_price,
        property_type=property_type,
        new_build=new_build,
        tenure=tenure,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        include_total=include_total,
    )