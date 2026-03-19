from pydantic import BaseModel, Field


class AreaOut(BaseModel):
    area_code: str = Field(
        ...,
        description="ONS-style administrative area code used across the API as a geographic join key.",
        examples=["E08000035"],
    )
    area_name: str = Field(
        ...,
        description="Human-readable administrative area name.",
        examples=["Leeds"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "area_code": "E08000035",
                "area_name": "Leeds",
            }
        }
    }
