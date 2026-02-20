from pydantic import BaseModel, Field
from typing import Optional

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
