from pydantic import BaseModel
from typing import Optional

class AreaOut(BaseModel):
    area_code: Optional[str] = None
    area_name: Optional[str] = None