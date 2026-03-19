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
    postcode: str = Field(..., min_length=2, max_length=12, description="UK postcode (normalized in service).", examples=["LS29JT"])
    area_code: Optional[str] = Field(None, min_length=3, max_length=12, description="Area code, e.g. E08000035.", examples=["E08000035"])
    time_period: str = Field(..., description="YYYY-MM, e.g. 2024-07.", examples=["2025-02"])
    rent: float = Field(..., gt=0, description="Monthly rent in GBP.", examples=[1250.0])
    bedrooms: Optional[int] = Field(None, ge=0, le=10, description="Number of bedrooms.", examples=[2])
    property_type: Optional[PropertyType] = Field(None, description="Property type category.", examples=["flat"])
    source: SourceType = Field(default="user", description="Origin of the submitted rental record.", examples=["user"])

class RentalRecordCreate(RentalRecordBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "LS29JT",
                "time_period": "2025-02",
                "rent": 1250.0,
                "bedrooms": 2,
                "property_type": "flat",
                "source": "user",
            }
        }
    }

class RentalRecordUpdate(BaseModel):
    postcode: Optional[str] = Field(None, min_length=2, max_length=12, examples=["LS29JT"])
    area_code: Optional[str] = Field(None, min_length=3, max_length=12, examples=["E08000035"])
    time_period: Optional[str] = Field(None, examples=["2025-02"])
    rent: Optional[float] = Field(None, gt=0, examples=[1250.0])
    bedrooms: Optional[int] = Field(None, ge=0, le=10, examples=[2])
    property_type: Optional[PropertyType] = Field(None, examples=["flat"])
    source: Optional[SourceType] = Field(None, examples=["user"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "LS29JT",
                "time_period": "2025-02",
                "rent": 1250.0,
                "bedrooms": 2,
                "property_type": "flat",
                "source": "user",
            }
        }
    }

class RentalRecordOut(RentalRecordBase):
    id: int = Field(description="Primary key of the stored rental record.", examples=[14])
    created_at: str = Field(description="Timestamp recorded when the rental record was created.", examples=["2026-03-19T10:20:11"])
    uploader_id: int = Field(description="Authenticated user id of the record uploader.", examples=[1])

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 14,
                "postcode": "LS29JT",
                "area_code": "E08000035",
                "time_period": "2025-02",
                "rent": 1250.0,
                "bedrooms": 2,
                "property_type": "flat",
                "source": "user",
                "created_at": "2026-03-19T10:20:11",
                "uploader_id": 1,
            }
        }
    }

class RentalRecordListOut(BaseModel):
    items: list[RentalRecordOut] = Field(description="List of user-contributed rental records.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": 14,
                        "postcode": "LS29JT",
                        "area_code": "E08000035",
                        "time_period": "2025-02",
                        "rent": 1250.0,
                        "bedrooms": 2,
                        "property_type": "flat",
                        "source": "user",
                        "created_at": "2026-03-19T10:20:11",
                        "uploader_id": 1,
                    }
                ]
            }
        }
    }

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
