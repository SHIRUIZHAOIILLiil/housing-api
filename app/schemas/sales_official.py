from datetime import date
from typing import Literal, Optional, TypeVar, Generic, List
from pydantic import BaseModel, Field, ConfigDict


PropertyType = Literal["D", "S", "T", "F", "O"]  # Detached/Semi/Terraced/Flat/Other
NewBuildFlag = Literal["Y", "N"]
TenureType = Literal["F", "L", "U"]  # Freehold/Leasehold/Unknown

SortBy = Literal["transaction_date", "price"]
SortOrder = Literal["asc", "desc"]

T = TypeVar("T")

class Links(BaseModel):
    self: str = Field(..., examples=["/official/sales-transactions/44F406B7-3032-1095-E063-4704A8C048D4"])

class OfficialSalesTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_uuid: str = Field(..., description="HM Land Registry transaction UUID")
    price: float = Field(..., ge=0, description="Sale price in GBP")
    transaction_date: date = Field(..., description="Completion date")
    postcode: str = Field(..., description="Normalized postcode (e.g., 'LS29 8PB')")
    area_code: Optional[str] = Field(None, description="Derived via postcode->area mapping")

    property_type: Optional[PropertyType] = Field(None, description="D/S/T/F/O")
    new_build: Optional[NewBuildFlag] = Field(None, description="Y if new build else N")
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
    new_build: Optional[NewBuildFlag] = None
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