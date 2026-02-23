from pydantic import BaseModel, Field
from typing import Optional

class AreaOut(BaseModel):
    area_code: str
    area_name: str