# models/serp_models.py
from pydantic import BaseModel
from typing import Optional

class SerpResult(BaseModel):
    rank: int
    title: str
    url: str
    snippet: Optional[str] = None
