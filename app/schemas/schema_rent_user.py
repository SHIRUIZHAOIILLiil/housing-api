from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal
import re

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

PropertyType = Literal[
    "flat",
    "terraced",
    "semidetached",
    "detached",
    "other",
]

SourceType = Literal["user", "survey", "partner"]

class RentalRecordBase(BaseModel):
    postcode: str = Field(..., min_length=2, max_length=12, description="UK postcode (normalized in service).")
    area_code: Optional[str] = Field(None, min_length=3, max_length=12, description="Area code, e.g. E08000035.")
    time_period: str = Field(..., description="YYYY-MM, e.g. 2024-07.")
    rent: float = Field(..., gt=0, description="Monthly rent in GBP.")
    bedrooms: Optional[int] = Field(None, ge=0, le=10, description="Number of bedrooms.")
    property_type: Optional[PropertyType] = Field(None, description="Property type category.")
    source: SourceType = "user"

class RentalRecordCreate(RentalRecordBase):
    pass

class RentalRecordUpdate(BaseModel):
    postcode: Optional[str] = Field(None, min_length=2, max_length=12)
    area_code: Optional[str] = Field(None, min_length=3, max_length=12)
    time_period: Optional[str] = None
    rent: Optional[float] = Field(None, gt=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=10)
    property_type: Optional[PropertyType] = None
    source: Optional[SourceType] = None

class RentalRecordOut(RentalRecordBase):
    id: int
    created_at: str

class RentalRecordListOut(BaseModel):
    items: list[RentalRecordOut]

class RentalRecordPatch(BaseModel):
    postcode: Optional[str] = Field(None, min_length=2, max_length=12, examples=["LS1 1AA"])
    area_code: Optional[str] = Field(None, min_length=3, max_length=12, examples=["E08000035"])
    time_period: Optional[str] = Field(None, examples=["2024-07"])
    rent: Optional[float] = Field(None, gt=0, examples=[950])
    bedrooms: Optional[int] = Field(None, ge=0, le=10, examples=[2])
    property_type: Optional[PropertyType] = Field(None, examples=["flat"])
    source: Optional[SourceType] = Field(None, examples=["user"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"rent": 999},
                {"bedrooms": 2, "property_type": "flat"},
                {"time_period": "2024-07", "rent": 1100}
            ]
        }
    }