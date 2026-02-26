from __future__ import annotations

import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends
from app.api.deps import get_sales_global_filters, get_sales_scoped_filters , get_conn, COMMON_ERROR_RESPONSES

from app.schemas.sales_official import (
    OfficialSalesTransactionOut,
    PagedResponse,
    PageMeta,
    PageLinks,
    SalesTransactionsQuery,
    SalesGlobalFilters,
    SalesScopedFilters,
    SalesStatsOut,
    SalesStatsSeriesOut,
    SalesStatsAvailabilityOut,
    SalesStatsPointQuery,
    SalesStatsSeriesQuery,
    SalesStatsLatestQuery,
)
from app.services.service_sales_official import (
    list_official_sales_transactions,
    get_official_sales_transaction_by_uuid,
    list_official_sales_transactions_by_area,
    list_official_sales_transactions_by_postcode,
    get_official_sales_stats_point,
    list_official_sales_stats_series,
    get_official_sales_stats_latest,
    get_official_sales_stats_availability,
)

router = APIRouter()


def _build_page_links(base_path: str, filters: SalesTransactionsQuery, count: int) -> PageLinks:
    """
    Generates a `self/next/prev` link (relative path) for pagination navigation.
    `base_path`: e.g., "/official/sales-transactions"
    """
    # Only return the necessary query parameters
    def qs(offset: int) -> str:
        parts: list[str] = []
        uuid_prefix = getattr(filters, "uuid_prefix", None)
        if uuid_prefix:
            parts.append(f"uuid_prefix={uuid_prefix}")

        postcode_like = getattr(filters, "postcode_like", None)
        if postcode_like:
            parts.append(f"postcode_like={postcode_like}")

        if filters.date_from:
            parts.append(f"date_from={filters.date_from.isoformat()}")
        if filters.date_to:
            parts.append(f"date_to={filters.date_to.isoformat()}")
        if filters.min_price is not None:
            parts.append(f"min_price={filters.min_price}")
        if filters.max_price is not None:
            parts.append(f"max_price={filters.max_price}")
        if filters.property_type:
            parts.append(f"property_type={filters.property_type}")
        if filters.new_build:
            parts.append(f"new_build={filters.new_build}")
        if filters.tenure:
            parts.append(f"tenure={filters.tenure}")

        parts.append(f"limit={filters.limit}")
        parts.append(f"offset={offset}")
        parts.append(f"sort_by={filters.sort_by}")
        parts.append(f"order={filters.order}")

        return "&".join(parts)

    self_url = f"{base_path}?{qs(filters.offset)}"
    next_url = None
    prev_url = None

    # next: When the number of items returned on the current page equals limit,
    # it usually means "there may be a next page".
    if count == filters.limit:
        next_url = f"{base_path}?{qs(filters.offset + filters.limit)}"

    # `prev`: The previous page is only displayed if `offset - limit >= 0`.
    if filters.offset > 0:
        prev_offset = max(0, filters.offset - filters.limit)
        prev_url = f"{base_path}?{qs(prev_offset)}"

    return PageLinks(self=self_url, next=next_url, prev=prev_url)

def attach_transaction_links(item: list[dict]) -> None:
    """
    Mutates item dict by adding hypermedia links.
    """
    uuid = item.get("transaction_uuid")
    postcode = item.get("postcode")
    area_code = item.get("area_code")

    links = {
        "self": f"/transactions/sales_official/{uuid}",
    }

    if postcode:
        links["postcode"] = f"/postcodes/{postcode}"

    if area_code:
        links["area"] = f"/areas/{area_code}"

    item["links"] = links


@router.get(
    "",
    response_model=PagedResponse[OfficialSalesTransactionOut],
    summary="List official sales transactions (supports search/filtering)",
    responses=COMMON_ERROR_RESPONSES
)
def api_list_official_sales_transactions(
    filters: SalesGlobalFilters = Depends(get_sales_global_filters),
    conn: sqlite3.Connection = Depends(get_conn),
):
    items, total = list_official_sales_transactions(conn, filters)

    meta = PageMeta(
        limit=filters.limit,
        offset=filters.offset,
        count=len(items),
        total=total,
    )

    for item in items:
        attach_transaction_links(item)

    links = _build_page_links("/official/sales-transactions", filters, count=len(items))

    return PagedResponse(items=items, meta=meta, links=links)


@router.get(
    "/transactions/{transaction_uuid}",
    response_model=OfficialSalesTransactionOut,
    summary="Get a specific sales transaction",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_official_sales_transaction(
    transaction_uuid: UUID,
    conn: sqlite3.Connection = Depends(get_conn),
):
    item = get_official_sales_transaction_by_uuid(conn, str(transaction_uuid))  # service will throw NotFoundError
    attach_transaction_links(item)
    item["links"] = {
        "self": f"/sales-transactions/transactions/{item['transaction_uuid']}",
        "area": f"sales-transactions/areas/{item['area_code']}/sales-transactions" if item.get("area_code") else None,
        "postcode": f"sales-transactions/postcodes/{item['postcode']}/sales-transactions",
    }
    return item


@router.get(
    "/areas/{area_code}",
    response_model=PagedResponse[OfficialSalesTransactionOut],
    summary="List official sales transactions for a given area (supports filtering)",
    responses=COMMON_ERROR_RESPONSES
)
def api_list_official_sales_by_area(
    area_code: str,
    filters: SalesScopedFilters = Depends(get_sales_scoped_filters),
    conn: sqlite3.Connection = Depends(get_conn),
):
    items, total = list_official_sales_transactions_by_area(conn, area_code, filters)

    meta = PageMeta(limit=filters.limit, offset=filters.offset, count=len(items), total=total)
    base = f"/official/areas/{area_code}/sales-transactions"

    for item in items:
        attach_transaction_links(item)

    links = _build_page_links(base, filters, count=len(items))

    return PagedResponse(items=items, meta=meta, links=links)


@router.get(
    "/postcodes/{postcode}",
    response_model=PagedResponse[OfficialSalesTransactionOut],
    summary="List official sales transactions for a given postcode (supports filtering)",
    responses=COMMON_ERROR_RESPONSES
)
def api_list_official_sales_by_postcode(
    postcode: str,
    filters: SalesScopedFilters = Depends(get_sales_scoped_filters),
    conn: sqlite3.Connection = Depends(get_conn),
):

    items, total = list_official_sales_transactions_by_postcode(conn, postcode, filters)

    meta = PageMeta(limit=filters.limit, offset=filters.offset, count=len(items), total=total)
    base = f"/official/postcodes/{postcode}/sales-transactions"

    for item in items:
        attach_transaction_links(item)

    links = _build_page_links(base, filters, count=len(items))

    return PagedResponse(items=items, meta=meta, links=links)

@router.get(
    "/sales-stats",
    response_model=SalesStatsOut,
    summary="Get aggregated official sales stats for an area and month",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_official_sales_stats_point(
    area_code: str,
    time_period: str,
    filters: SalesStatsPointQuery = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
):
    # 400: time_period format
    result = get_official_sales_stats_point(conn, area_code, time_period, filters)

    # echo filters
    result["property_type"] = filters.property_type
    result["new_build"] = filters.new_build
    result["tenure"] = filters.tenure
    return result

@router.get(
    "/areas/{area_code}/sales-stats",
    response_model=SalesStatsSeriesOut,
    summary="Get time-series of aggregated official sales stats for an area",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_official_sales_stats_series(
    area_code: str,
    filters: SalesStatsSeriesQuery = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
):
    items, total = list_official_sales_stats_series(conn, area_code, filters)
    return {"area_code": area_code, "items": items, "total": total, "limit": filters.limit, "offset": filters.offset,}

@router.get(
    "/areas/{area_code}/sales-stats/latest",
    response_model=SalesStatsOut,
    summary="Get latest available aggregated official sales stats for an area",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_official_sales_stats_latest(
    area_code: str,
    filters: SalesStatsLatestQuery = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
):
    result = get_official_sales_stats_latest(conn, area_code, filters)

    # echo filters
    result["property_type"] = filters.property_type
    result["new_build"] = filters.new_build
    result["tenure"] = filters.tenure
    return result


@router.get(
    "/areas/{area_code}/sales-stats/availability",
    response_model=SalesStatsAvailabilityOut,
    summary="Get min/max months available for official sales stats in an area",
    responses=COMMON_ERROR_RESPONSES
)
def api_get_official_sales_stats_availability(
    area_code: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    result = get_official_sales_stats_availability(conn, area_code)
    return result
