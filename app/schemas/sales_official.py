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
    self: str = Field(..., examples=["sales_official/44F406B7-3032-1095-E063-4704A8C048D4"])

class OfficialSalesTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_uuid: str = Field(..., description="HM Land Registry transaction UUID")
    price: float = Field(..., ge=0, description="Sale price in GBP")
    transaction_date: date = Field(..., description="Completion date")
    postcode: str = Field(..., description="Normalized postcode (e.g., 'LS29 8PB')")
    area_code: Optional[str] = Field(None, description="Derived via postcode->area mapping")

    property_type: Optional[PropertyType] = Field(None, description="D/S/T/F/O")
    new_build: Optional[bool] = None
    tenure: Optional[TenureType] = Field(None, description="F/L/U")

    paon: Optional[str] = Field(None, description="Primary Addressable Object Name/Number")
    saon: Optional[str] = Field(None, description="Secondary Addressable Object Name/Number")

    links: Optional[Links] = None


class SalesTransactionsQuery(BaseModel):

    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    new_build: Optional[bool] = None
    tenure: Optional[TenureType] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    sort_by: SortBy = "transaction_date"
    order: SortOrder = "desc"
    include_total: bool = False

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
    limit: int
    offset: int
    count: int
    total: Optional[int] = None

class PageLinks(BaseModel):
    self: str
    next: Optional[str] = None
    prev: Optional[str] = None

class PagedResponse(BaseModel, Generic[T]):
    items: List[T]
    meta: PageMeta
    links: Optional[PageLinks] = None

class SalesStatsOut(BaseModel):
    area_code: str
    time_period: str = Field(..., description="YYYY-MM")

    count: int
    avg_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    total_value: Optional[float] = None  # SUM(price)

    # Echoing the filter back allows the client to understand "under what conditions it was calculated".
    property_type: Optional[PropertyType] = None
    new_build: Optional[bool] = None
    tenure: Optional[TenureType] = None


class SalesStatsSeriesPoint(BaseModel):
    time_period: str
    count: int
    avg_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    total_value: Optional[float] = None


class SalesStatsSeriesOut(BaseModel):
    area_code: str
    items: List[SalesStatsSeriesPoint]


class SalesStatsAvailabilityOut(BaseModel):
    area_code: str
    min_time_period: Optional[str] = None
    max_time_period: Optional[str] = None
    months: int = 0

class SalesStatsPointQuery(BaseModel):
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    new_build: Optional[bool] = Field(None, description="Filter by new build: true=1, false=0 in DB")
    tenure: Optional[TenureType] = None


class SalesStatsSeriesQuery(BaseModel):
    """
        Filters for stats: Reuse the core of transaction filters, but use month-level from/to.
    """
    from_period: Optional[str] = Field(None, alias="date_from", description="YYYY-MM")
    to_period: Optional[str] = Field(None, alias="date_to", description="YYYY-MM")

    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    new_build: Optional[bool] = None
    tenure: Optional[TenureType] = None

    limit: int = Field(240, ge=1, le=500)
    offset: int = Field(0, ge=0)

class SalesStatsLatestQuery(BaseModel):
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    new_build: Optional[bool] = None
    tenure: Optional[TenureType] = None
