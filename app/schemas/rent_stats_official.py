from pydantic import BaseModel, Field
from typing import Literal, Optional

YYYY_MM = r"^\d{4}-(0[1-9]|1[0-2])$"

class BedStats(BaseModel):
    index: Optional[float] = Field(
        default=None,
        description="Rental price index value for the selected bedroom group.",
        examples=[78.770196],
    )
    rental_price: Optional[float] = Field(
        default=None,
        description="Monthly rental price in GBP for the selected bedroom group.",
        examples=[780.0],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "index": 78.770196,
                "rental_price": 780.0,
            }
        }
    }

class OverallStats(BedStats):
    annual_change: Optional[float] = Field(
        default=None,
        description="Annual percentage change for the overall rent series.",
        examples=[5.226974],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "index": 78.770196,
                "rental_price": 780.0,
                "annual_change": 5.226974,
            }
        }
    }

class PropertyTypePrices(BaseModel):
    detached: Optional[float] = Field(default=None, description="Monthly rent for detached properties.", examples=[1041.0])
    semidetached: Optional[float] = Field(default=None, description="Monthly rent for semi-detached properties.", examples=[831.0])
    terraced: Optional[float] = Field(default=None, description="Monthly rent for terraced properties.", examples=[784.0])
    flat_maisonette: Optional[float] = Field(default=None, description="Monthly rent for flats or maisonettes.", examples=[622.0])

    model_config = {
        "json_schema_extra": {
            "example": {
                "detached": 1041.0,
                "semidetached": 831.0,
                "terraced": 784.0,
                "flat_maisonette": 622.0,
            }
        }
    }


class RentStatsOfficialOut(BaseModel):
    time_period:str = Field(
        title="Time period",
        description="Monthly observation period in YYYY-MM format.",
        pattern=YYYY_MM,
        examples=["2017-06"],
    )
    area_code: str = Field(
        ...,
        description="Administrative area code for the rent observation.",
        examples=["E08000035"],
    )
    region_or_country_name: Optional[str] = Field(
        default=None,
        description="Higher-level region or country label from the source dataset.",
        examples=["Yorkshire and The Humber"],
    )
    overall: OverallStats = Field(..., description="Overall monthly rent statistics for the area.")
    one_bed: Optional[BedStats] = Field(default=None, description="One-bedroom monthly rent statistics, when available.")
    two_bed: Optional[BedStats] = Field(default=None, description="Two-bedroom monthly rent statistics, when available.")
    three_bed: Optional[BedStats] = Field(default=None, description="Three-bedroom monthly rent statistics, when available.")
    property_prices: Optional[PropertyTypePrices] = Field(
        default=None,
        description="Property-type level rent prices for the area and month, when available.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "time_period": "2017-06",
                "area_code": "E08000035",
                "region_or_country_name": "Yorkshire and The Humber",
                "overall": {
                    "index": 78.770196,
                    "rental_price": 780.0,
                    "annual_change": 5.226974,
                },
                "one_bed": {
                    "index": 79.698707,
                    "rental_price": 527.0,
                },
                "two_bed": {
                    "index": 79.964345,
                    "rental_price": 666.0,
                },
                "three_bed": {
                    "index": 78.549998,
                    "rental_price": 763.0,
                },
                "property_prices": {
                    "detached": 1041.0,
                    "semidetached": 831.0,
                    "terraced": 784.0,
                    "flat_maisonette": 622.0,
                },
            }
        }
    }

class RentStatsAvailabilityOut(BaseModel):
    area_code: str = Field(..., description="Area whose data availability is being described.", examples=["E08000035"])
    min_time_period: Optional[str] = Field(default=None, description="Earliest available month for the area.", pattern=YYYY_MM, examples=["2017-02"])
    max_time_period: Optional[str] = Field(default=None, description="Latest available month for the area.", pattern=YYYY_MM, examples=["2017-06"])
    count: int = Field(default=0, description="Number of stored monthly observations for the area.", examples=[5])

    model_config = {
        "json_schema_extra": {
            "example": {
                "area_code": "E08000035",
                "min_time_period": "2017-02",
                "max_time_period": "2017-06",
                "count": 5,
            }
        }
    }


class RentMapPointOut(BaseModel):
    area_code: str = Field(..., description="Administrative area code used to join the map snapshot to the boundary GeoJSON.", examples=["E08000035"])
    area_name: str = Field(..., description="Display name of the mapped area.", examples=["Leeds"])
    region_or_country_name: Optional[str] = Field(default=None, description="Higher-level region or country label.", examples=["Yorkshire and The Humber"])
    time_period: str = Field(title="Time period", description="Snapshot month in YYYY-MM format.", pattern=YYYY_MM, examples=["2017-06"])
    value: float = Field(..., description="Selected metric value used to colour the map.", examples=[780.0])
    rental_price: Optional[float] = Field(default=None, description="Overall rental price for the snapshot month.", examples=[780.0])
    index_value: Optional[float] = Field(default=None, description="Overall index value for the snapshot month.", examples=[78.770196])
    annual_change: Optional[float] = Field(default=None, description="Overall annual percentage change for the snapshot month.", examples=[5.226974])

    model_config = {
        "json_schema_extra": {
            "example": {
                "area_code": "E08000035",
                "area_name": "Leeds",
                "region_or_country_name": "Yorkshire and The Humber",
                "time_period": "2017-06",
                "value": 780.0,
                "rental_price": 780.0,
                "index_value": 78.770196,
                "annual_change": 5.226974,
            }
        }
    }


class RentMapSummaryOut(BaseModel):
    requested_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM, description="Optional month requested by the client. Null means the API used the latest available month.", examples=[None])
    resolved_time_period: str = Field(pattern=YYYY_MM, description="Actual snapshot month returned by the API.", examples=["2017-06"])
    min_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM, description="Earliest month available in the official rent dataset.", examples=["2017-02"])
    max_time_period: Optional[str] = Field(default=None, pattern=YYYY_MM, description="Latest month available in the official rent dataset.", examples=["2017-06"])
    metric: Literal["rental_price", "index_value", "annual_change"] = Field(description="Metric selected for map colouring.", examples=["rental_price"])
    bedrooms: Literal["overall", "1", "2", "3"] = Field(description="Bedroom grouping applied to the selected metric.", examples=["overall"])
    item_count: int = Field(description="Number of areas returned in the snapshot.", examples=[3])
    items: list[RentMapPointOut] = Field(description="Per-area snapshot values used by the map page.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "requested_time_period": None,
                "resolved_time_period": "2017-06",
                "min_time_period": "2017-02",
                "max_time_period": "2017-06",
                "metric": "rental_price",
                "bedrooms": "overall",
                "item_count": 3,
                "items": [
                    {
                        "area_code": "E07000240",
                        "area_name": "St Albans",
                        "region_or_country_name": "East of England",
                        "time_period": "2017-06",
                        "value": 1347.0,
                        "rental_price": 1347.0,
                        "index_value": 84.536721,
                        "annual_change": 3.911254,
                    },
                    {
                        "area_code": "E08000035",
                        "area_name": "Leeds",
                        "region_or_country_name": "Yorkshire and The Humber",
                        "time_period": "2017-06",
                        "value": 780.0,
                        "rental_price": 780.0,
                        "index_value": 78.770196,
                        "annual_change": 5.226974,
                    },
                ],
            }
        }
    }
