from pydantic import BaseModel
from typing import Optional

class BedStats(BaseModel):
    index: Optional[float] = None
    rental_price: Optional[float] = None


class RentStatsOfficialOut(BaseModel):
    time_period:str
    area_code: str

    region_or_country_name: Optional[str] = None
    index_value: Optional[float] = None
    annual_change: Optional[float] = None
    rental_price: Optional[float] = None

    overall: BedStats
    one_bed: Optional[BedStats] = None
    two_bed: Optional[BedStats] = None
    three_bed: Optional[BedStats] = None

    detached_price: Optional[float] = None
    semidetached_price: Optional[float] = None
    terraced_price: Optional[float] = None
    flat_maisonette_price: Optional[float] = None


