from pydantic import BaseModel

class AreaOut(BaseModel):
    area_code: str
    area_name: str