from __future__ import annotations

import re
from typing import Optional, Literal
from pydantic import BaseModel, Field

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

PropertyType = Literal["flat", "terraced", "semidetached", "detached", "other"]
SourceType = Literal["user", "survey", "partner"]


class SalesUserBase(BaseModel):
    postcode: str = Field(..., min_length=2, max_length=12, description="Normalized postcode for the submitted sale.", examples=["LS29JT"])
    area_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=12,
        description="Optional. If omitted, will be derived from postcode_map.",
        examples=["E08000035"],
    )
    time_period: str = Field(..., description="YYYY-MM", examples=["2025-02"])
    price: float = Field(..., gt=0, description="Transaction price in GBP.", examples=[315000.0])
    property_type: Optional[PropertyType] = Field(default=None, description="Normalized property type category.", examples=["semidetached"])
    source: SourceType = Field(default="user", description="Origin of the submitted sales record.", examples=["user"])


class SalesUserCreate(SalesUserBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "LS29JT",
                "time_period": "2025-02",
                "price": 315000.0,
                "property_type": "semidetached",
                "source": "user",
            }
        }
    }


class SalesUserOut(SalesUserBase):
    id: int = Field(description="Primary key of the stored user sale record.", examples=[7])
    created_at: str = Field(description="Timestamp recorded when the user sale record was created.", examples=["2026-03-19T10:20:11"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 7,
                "postcode": "LS29JT",
                "area_code": "E08000035",
                "time_period": "2025-02",
                "price": 315000.0,
                "property_type": "semidetached",
                "source": "user",
                "created_at": "2026-03-19T10:20:11",
            }
        }
    }


class SalesUserListOut(BaseModel):
    items: list[SalesUserOut] = Field(description="List of user-contributed sales records.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": 7,
                        "postcode": "LS29JT",
                        "area_code": "E08000035",
                        "time_period": "2025-02",
                        "price": 315000.0,
                        "property_type": "semidetached",
                        "source": "user",
                        "created_at": "2026-03-19T10:20:11",
                    }
                ]
            }
        }
    }


class SalesUserPatch(BaseModel):
    # PATCH: Only update the fields provided.
    # Modifying postcode/area_code/source is not allowed (to avoid "moving/changing lineage")
    time_period: Optional[str] = Field(None, examples=["2024-08"])
    price: Optional[float] = Field(None, gt=0, examples=[275000])
    property_type: Optional[PropertyType] = Field(None, examples=["flat"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"price": 300000},
                {"time_period": "2024-08"},
                {"price": 315000, "property_type": "semidetached"},
            ]
        }
    }
