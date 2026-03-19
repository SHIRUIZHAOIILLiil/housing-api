from pydantic import BaseModel, Field
from typing import Literal, Optional

YYYY_MM = r"^\d{4}-(0[1-9]|1[0-2])$"

class BedStats(BaseModel):
    index: Optional[float] = None
    rental_price: Optional[float] = None

class OverallStats(BedStats):
    annual_change: Optional[float] = None

class PropertyTypePrices(BaseModel):
    detached: Optional[float] = None
    semidetached: Optional[float] = None
    terraced: Optional[float] = None
    flat_maisonette: Optional[float] = None


class RentStatsOfficialOut(BaseModel):
    time_period:str = Field(title="Time period", description="Time period", pattern=YYYY_MM)
    area_code: str

    region_or_country_name: Optional[str] = None

    overall: OverallStats
    one_bed: Optional[BedStats] = None
    two_bed: Optional[BedStats] = None
    three_bed: Optional[BedStats] = None

    property_prices: Optional[PropertyTypePrices] = None

class RentStatsAvailabilityOut(BaseModel):
    area_code: str
    min_time_period: Optional[str] = None
    max_time_period: Optional[str] = None
    count: int = 0


class RentMapPointOut(BaseModel):
    area_code: str
    area_name: str
    region_or_country_name: Optional[str] = None
    time_period: str = Field(title="Time period", description="Time period", pattern=YYYY_MM)
    value: float
    rental_price: Optional[float] = None
    index_value: Optional[float] = None
    annual_change: Optional[float] = None


class RentMapSummaryOut(BaseModel):
    requested_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM)
    resolved_time_period: str = Field(pattern=YYYY_MM)
    min_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM)
    max_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM)
    metric: Literal["rental_price", "index_value", "annual_change"]
    bedrooms: Literal["overall", "1", "2", "3"]
    item_count: int
    items: list[RentMapPointOut]
