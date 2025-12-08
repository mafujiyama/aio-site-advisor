# agents/serp_agent.py

from typing import List
from models.serp_models import SerpResult
from services.serp_client import search_serp_mock


def fetch_serp_for_keyword(keyword: str, limit: int = 5) -> List[SerpResult]:
    """
    指定したキーワードに対して SERP（検索結果）のリストを取得するエージェント。
    現時点ではモック実装（search_serp_mock）を使用。
    将来、実際のSerpAPIやGoogle Custom Search APIに差し替え予定。
    """
    return search_serp_mock(query=keyword, limit=limit)
