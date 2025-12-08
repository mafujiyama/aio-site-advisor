# models/keyword_models.py
from pydantic import BaseModel
from typing import List, Literal, Optional

IntentType = Literal["KNOW", "COMPARE", "BUY", "NAVIGATIONAL"]

class KeywordItem(BaseModel):
    keyword: str
    intent: IntentType
    category: str
    priority: int  # 1〜5 の優先度
    reason: Optional[str] = None

class KeywordPlan(BaseModel):
    seed_keyword: str
    items: List[KeywordItem]

    def top_keywords(self, limit: int = 10) -> List[KeywordItem]:
        return sorted(self.items, key=lambda k: k.priority, reverse=True)[:limit]
