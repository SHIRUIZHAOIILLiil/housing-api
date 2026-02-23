from __future__ import annotations

import re
from typing import Optional, Literal
from pydantic import BaseModel, Field

YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

PropertyType = Literal["flat", "terraced", "semidetached", "detached", "other"]
SourceType = Literal["user", "survey", "partner"]


class SalesUserBase(BaseModel):
    postcode: str = Field(..., min_length=2, max_length=12)
    area_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=12,
        description="Optional. If omitted, will be derived from postcode_map.",
    )
    time_period: str = Field(..., description="YYYY-MM")
    price: float = Field(..., gt=0, description="Transaction price in GBP.")
    property_type: Optional[PropertyType] = None
    source: SourceType = "user"


class SalesUserCreate(SalesUserBase):
    # Post version
    pass


class SalesUserOut(SalesUserBase):
    id: int
    created_at: str


class SalesUserListOut(BaseModel):
    items: list[SalesUserOut]


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
