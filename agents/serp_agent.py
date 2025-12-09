# agents/serp_agent.py

from typing import List
from models.serp_models import SerpResult
from services.serp_client import fetch_serp_google


def fetch_serp_for_keyword(keyword: str, limit: int = 5) -> List[SerpResult]:
    """キーワード単位で SERP を取得するラッパー。"""
    return fetch_serp_google(keyword, limit=limit)
