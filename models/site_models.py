# models/site_models.py
from pydantic import BaseModel
from typing import List, Optional

class Heading(BaseModel):
    level: int              # 1,2,3 など (h1, h2, h3)
    text: str

class SiteStructure(BaseModel):
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None

    h1_list: List[str] = []
    headings: List[Heading] = []  # h2, h3 など

    main_text: Optional[str] = None
    word_count: int = 0
