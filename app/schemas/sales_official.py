import re
from datetime import date
from typing import Literal, Optional, TypeVar, Generic, List
from pydantic import BaseModel, Field, ConfigDict


PropertyType = Literal["D", "S", "T", "F", "O"]  # Detached/Semi/Terraced/Flat/Other
TenureType = Literal["F", "L", "U"]  # Freehold/Leasehold/Unknown

SortBy = Literal["transaction_date", "price"]
SortOrder = Literal["asc", "desc"]

T = TypeVar("T")

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

class Links(BaseModel):
    self: str = Field(..., description="Canonical self link for the returned resource.", examples=["/sales_official/transactions/44F406B7-3032-1095-E063-4704A8C048D4"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "self": "/sales_official/transactions/44F406B7-3032-1095-E063-4704A8C048D4",
            }
        }
    )

class OfficialSalesTransactionOut(BaseModel):
    transaction_uuid: str = Field(..., description="HM Land Registry transaction UUID")
    price: float = Field(..., ge=0, description="Sale price in GBP")
    transaction_date: date = Field(..., description="Completion date")
    postcode: str = Field(..., description="Normalized postcode (e.g., 'LS29 8PB')")
    area_code: Optional[str] = Field(None, description="Derived via postcode->area mapping")

    property_type: Optional[PropertyType] = Field(None, description="Property type code: D/S/T/F/O.", examples=["S"])
    new_build: Optional[bool] = Field(None, description="Whether the transaction is marked as a new build.", examples=[False])
    tenure: Optional[TenureType] = Field(None, description="Tenure code: F/L/U.", examples=["F"])

    paon: Optional[str] = Field(None, description="Primary Addressable Object Name/Number")
    saon: Optional[str] = Field(None, description="Secondary Addressable Object Name/Number")

    links: Optional[Links] = Field(default=None, description="Hypermedia links related to the transaction.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transaction_uuid": "44F406B7-3032-1095-E063-4704A8C048D4",
                "price": 427500.0,
                "transaction_date": "2020-08-14",
                "postcode": "LS29 8PB",
                "area_code": "E08000035",
                "property_type": "S",
                "new_build": False,
                "tenure": "F",
                "paon": "12",
                "saon": None,
                "links": {
                    "self": "/sales_official/transactions/44F406B7-3032-1095-E063-4704A8C048D4",
                },
            }
        },
    )


class SalesTransactionsQuery(BaseModel):

    date_from: Optional[date] = Field(default=None, description="Start transaction date filter (YYYY-MM-DD).", examples=["2020-01-01"])
    date_to: Optional[date] = Field(default=None, description="End transaction date filter (YYYY-MM-DD).", examples=["2020-12-31"])
    min_price: Optional[float] = Field(default=None, ge=0, description="Minimum transaction price.", examples=[100000])
    max_price: Optional[float] = Field(default=None, ge=0, description="Maximum transaction price.", examples=[500000])
    property_type: Optional[PropertyType] = Field(default=None, description="Property type filter.", examples=["S"])
    new_build: Optional[bool] = Field(default=None, description="Filter for new-build transactions.", examples=[False])
    tenure: Optional[TenureType] = Field(default=None, description="Tenure filter.", examples=["F"])
    limit: int = Field(50, ge=1, le=200, description="Maximum number of rows to return.", examples=[50])
    offset: int = Field(0, ge=0, description="Number of rows to skip before returning results.", examples=[0])
    sort_by: SortBy = Field(default="transaction_date", description="Field used for result ordering.", examples=["transaction_date"])
    order: SortOrder = Field(default="desc", description="Sort direction.", examples=["desc"])
    include_total: bool = Field(default=False, description="Include total match count for pagination metadata.", examples=[True])

class SalesGlobalFilters(SalesTransactionsQuery):
    postcode_like: Optional[str] = Field(
        None,
        description="Fuzzy postcode search (ignores spaces), e.g. 'LS7' or 'LS71EH'."
    )
    uuid_prefix: Optional[str] = Field(
        None,
        description="Transaction UUID prefix, e.g. '2859c1ad'."
    )

class SalesScopedFilters(SalesTransactionsQuery):
    """Used by /areas/{area_code}/... and /postcodes/{postcode}/... (no extra search fields)."""
    pass

class PageMeta(BaseModel):
    limit: int = Field(description="Requested page size.", examples=[50])
    offset: int = Field(description="Requested row offset.", examples=[0])
    count: int = Field(description="Number of items returned in the current page.", examples=[2])
    total: Optional[int] = Field(default=None, description="Total number of matching rows when include_total=true.", examples=[2])

class PageLinks(BaseModel):
    self: str = Field(description="Self link for the current page.", examples=["/official/sales-transactions?limit=50&offset=0&sort_by=transaction_date&order=desc"])
    next: Optional[str] = Field(default=None, description="Link for the next page, if one may exist.")
    prev: Optional[str] = Field(default=None, description="Link for the previous page, if one exists.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "self": "/official/sales-transactions?limit=50&offset=0&sort_by=transaction_date&order=desc",
                "next": "/official/sales-transactions?limit=50&offset=50&sort_by=transaction_date&order=desc",
                "prev": None,
            }
        }
    )

class PagedResponse(BaseModel, Generic[T]):
    items: List[T]
    meta: PageMeta
    links: Optional[PageLinks] = None

class SalesStatsOut(BaseModel):
    area_code: str = Field(..., description="Area whose aggregated sales snapshot is being reported.", examples=["E08000035"])
    time_period: str = Field(..., description="Monthly aggregation period in YYYY-MM format.", examples=["2020-08"])

    count: int = Field(description="Number of transactions included in the aggregate.", examples=[2])
    avg_price: Optional[float] = Field(default=None, description="Average sale price across the filtered transactions.", examples=[290500.0])
    min_price: Optional[float] = Field(default=None, description="Minimum sale price across the filtered transactions.", examples=[153500.0])
    max_price: Optional[float] = Field(default=None, description="Maximum sale price across the filtered transactions.", examples=[427500.0])
    total_value: Optional[float] = Field(default=None, description="Total transaction value across the filtered transactions.", examples=[581000.0])  # SUM(price)

    # Echoing the filter back allows the client to understand "under what conditions it was calculated".
    property_type: Optional[PropertyType] = Field(default=None, description="Optional property-type filter echoed back by the API.")
    new_build: Optional[bool] = Field(default=None, description="Optional new-build filter echoed back by the API.")
    tenure: Optional[TenureType] = Field(default=None, description="Optional tenure filter echoed back by the API.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_code": "E08000035",
                "time_period": "2020-08",
                "count": 2,
                "avg_price": 290500.0,
                "min_price": 153500.0,
                "max_price": 427500.0,
                "total_value": 581000.0,
                "property_type": None,
                "new_build": None,
                "tenure": None,
            }
        }
    )


class SalesStatsSeriesPoint(BaseModel):
    time_period: str = Field(description="Monthly aggregation period in YYYY-MM format.", examples=["2020-08"])
    count: int = Field(description="Number of transactions included in the monthly aggregate.", examples=[2])
    avg_price: Optional[float] = Field(default=None, description="Average sale price for the month.", examples=[290500.0])
    min_price: Optional[float] = Field(default=None, description="Minimum sale price for the month.", examples=[153500.0])
    max_price: Optional[float] = Field(default=None, description="Maximum sale price for the month.", examples=[427500.0])
    total_value: Optional[float] = Field(default=None, description="Total sale value for the month.", examples=[581000.0])


class SalesStatsSeriesOut(BaseModel):
    area_code: str = Field(description="Area whose monthly sales aggregates are being returned.", examples=["E08000035"])
    items: List[SalesStatsSeriesPoint] = Field(description="Ordered list of monthly aggregate points.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_code": "E08000035",
                "items": [
                    {
                        "time_period": "2020-07",
                        "count": 1,
                        "avg_price": 153500.0,
                        "min_price": 153500.0,
                        "max_price": 153500.0,
                        "total_value": 153500.0,
                    },
                    {
                        "time_period": "2020-08",
                        "count": 2,
                        "avg_price": 290500.0,
                        "min_price": 153500.0,
                        "max_price": 427500.0,
                        "total_value": 581000.0,
                    },
                ],
            }
        }
    )


class SalesStatsAvailabilityOut(BaseModel):
    area_code: str = Field(description="Area whose sales-statistics availability is being reported.", examples=["E08000035"])
    min_time_period: Optional[str] = Field(default=None, description="Earliest month available for the area.", examples=["2020-07"])
    max_time_period: Optional[str] = Field(default=None, description="Latest month available for the area.", examples=["2020-08"])
    months: int = Field(default=0, description="Number of months available in the aggregate table.", examples=[2])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_code": "E08000035",
                "min_time_period": "2020-07",
                "max_time_period": "2020-08",
                "months": 2,
            }
        }
    )

class SalesStatsPointQuery(BaseModel):
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter for the aggregate.", examples=[100000])
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter for the aggregate.", examples=[500000])
    property_type: Optional[PropertyType] = Field(default=None, description="Property type filter for the aggregate.", examples=["S"])
    new_build: Optional[bool] = Field(None, description="Filter by new build: true=1, false=0 in DB")
    tenure: Optional[TenureType] = Field(default=None, description="Tenure filter for the aggregate.", examples=["F"])


class SalesStatsSeriesQuery(BaseModel):
    """
        Filters for stats: Reuse the core of transaction filters, but use month-level from/to.
    """
    from_period: Optional[str] = Field(None, alias="date_from", description="YYYY-MM", examples=["2020-01"])
    to_period: Optional[str] = Field(None, alias="date_to", description="YYYY-MM", examples=["2020-12"])

    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter for the series.", examples=[100000])
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter for the series.", examples=[500000])
    property_type: Optional[PropertyType] = Field(default=None, description="Property type filter for the series.", examples=["S"])
    new_build: Optional[bool] = Field(default=None, description="Filter by new-build transactions in the series.", examples=[False])
    tenure: Optional[TenureType] = Field(default=None, description="Tenure filter for the series.", examples=["F"])

    limit: int = Field(240, ge=1, le=500, description="Maximum number of monthly points to return.", examples=[240])
    offset: int = Field(0, ge=0, description="Number of monthly points to skip before returning results.", examples=[0])

class SalesStatsLatestQuery(BaseModel):
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter for the latest aggregate.", examples=[100000])
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter for the latest aggregate.", examples=[500000])
    property_type: Optional[PropertyType] = Field(default=None, description="Property type filter for the latest aggregate.", examples=["S"])
    new_build: Optional[bool] = Field(default=None, description="Filter by new-build transactions for the latest aggregate.", examples=[False])
    tenure: Optional[TenureType] = Field(default=None, description="Tenure filter for the latest aggregate.", examples=["F"])
