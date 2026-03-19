from pydantic import BaseModel, Field


class PostcodeOut(BaseModel):
    postcode: str = Field(
        ...,
        description="Normalized postcode value returned by the postcode mapping dataset.",
        examples=["LS29JT"],
    )
    area_code: str = Field(
        ...,
        description="Resolved administrative area code for the postcode.",
        examples=["E08000035"],
    )
    area_name: str = Field(
        ...,
        description="Human-readable area name paired with the resolved area code.",
        examples=["Leeds"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "LS29JT",
                "area_code": "E08000035",
                "area_name": "Leeds",
            }
        }
    }
