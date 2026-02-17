from pydantic import BaseModel

class PostcodeOut(BaseModel):
    postcode: str
    area_code: str