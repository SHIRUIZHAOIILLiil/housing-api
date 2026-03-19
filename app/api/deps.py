import sqlite3
from typing import Generator, Optional
from fastapi import Query, Depends
from datetime import date
from app.core.config import Settings
from app.schemas.sales_official import (
    SalesGlobalFilters, SalesScopedFilters, PropertyType, TenureType, SortBy, SortOrder
)
from app.security.jwt import decode_access_token
from app.services.service_users import get_user_by_id
from app.schemas import UserOut

from app.schemas.errors import ErrorOut, UnauthorizedError
from fastapi.security import OAuth2PasswordBearer

settings = Settings()

COMMON_ERROR_RESPONSES = {
    400: {
        "model": ErrorOut,
        "description": "Invalid input.",
        "content": {"application/json": {"example": {"detail": "Invalid input"}}},
    },
    404: {
        "model": ErrorOut,
        "description": "Resource not found.",
        "content": {"application/json": {"example": {"detail": "Resource not found"}}},
    },
}

AUTH_ERROR_RESPONSES = {
    **COMMON_ERROR_RESPONSES,
    401: {
        "model": ErrorOut,
        "description": "Authentication failed or bearer token missing.",
        "content": {
            "application/json": {
                "examples": {
                    "missing_token": {"summary": "Missing bearer token", "value": {"detail": "Not authenticated"}},
                    "invalid_token": {"summary": "Invalid token", "value": {"detail": "Invalid token"}},
                }
            }
        },
    },
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_conn() -> Generator[sqlite3.Connection, None, None]:
    # FastAPI may serve sync dependencies and handlers on different worker threads.
    # Each request still gets its own connection, so disabling SQLite's same-thread
    # guard avoids false-positive thread errors on concurrent frontend requests.
    conn = sqlite3.connect(settings.DATABASE_DEMO, check_same_thread=False) # For full use, change it as settings.DATABASE
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_sales_global_filters(
    postcode_like: Optional[str] = Query(default=None, description="Fuzzy postcode (ignores spaces).", examples=["LS29"]),
    uuid_prefix: Optional[str] = Query(default=None, min_length=4, max_length=64, description="Transaction UUID prefix.", examples=["44f4"]),
    date_from: Optional[date] = Query(default=None, description="Start transaction date filter (YYYY-MM-DD).", examples=["2020-01-01"]),
    date_to: Optional[date] = Query(default=None, description="End transaction date filter (YYYY-MM-DD).", examples=["2020-12-31"]),
    min_price: Optional[int] = Query(default=None, ge=0, description="Minimum transaction price.", examples=[100000]),
    max_price: Optional[int] = Query(default=None, ge=0, description="Maximum transaction price.", examples=[500000]),
    property_type: Optional[PropertyType] = Query(default=None, description="Property type filter.", examples=["S"]),
    new_build: Optional[bool] = Query(default=None, description="Filter for new-build transactions.", examples=[False]),
    tenure: Optional[TenureType] = Query(default=None, description="Tenure filter.", examples=["F"]),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of rows to return.", examples=[50]),
    offset: int = Query(default=0, ge=0, description="Number of rows to skip before returning results.", examples=[0]),
    sort_by: SortBy = Query(default="transaction_date", description="Field used for result ordering.", examples=["transaction_date"]),
    order: SortOrder = Query(default="desc", description="Sort direction.", examples=["desc"]),
    include_total: bool = Query(default=False, description="Include total match count for pagination metadata.", examples=[True]),
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
    date_from: Optional[date] = Query(default=None, description="Start transaction date filter (YYYY-MM-DD).", examples=["2020-01-01"]),
    date_to: Optional[date] = Query(default=None, description="End transaction date filter (YYYY-MM-DD).", examples=["2020-12-31"]),
    min_price: Optional[int] = Query(default=None, ge=0, description="Minimum transaction price.", examples=[100000]),
    max_price: Optional[int] = Query(default=None, ge=0, description="Maximum transaction price.", examples=[500000]),
    property_type: Optional[PropertyType] = Query(default=None, description="Property type filter.", examples=["S"]),
    new_build: Optional[bool] = Query(default=None, description="Filter for new-build transactions.", examples=[False]),
    tenure: Optional[TenureType] = Query(default=None, description="Tenure filter.", examples=["F"]),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of rows to return.", examples=[50]),
    offset: int = Query(default=0, ge=0, description="Number of rows to skip before returning results.", examples=[0]),
    sort_by: SortBy = Query(default="transaction_date", description="Field used for result ordering.", examples=["transaction_date"]),
    order: SortOrder = Query(default="desc", description="Sort direction.", examples=["desc"]),
    include_total: bool = Query(default=False, description="Include total match count for pagination metadata.", examples=[True]),
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

def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """
    Extract user from JWT token.
    Raises UnauthorizedError if invalid.
    """
    user_id = decode_access_token(token)

    user = get_user_by_id(conn, user_id)
    if user is None:
        raise UnauthorizedError("Invalid token")

    return UserOut(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
    )
