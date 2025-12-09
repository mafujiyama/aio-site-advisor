# services/serp_client.py

from __future__ import annotations

import logging
from typing import List

import requests

from app.config import settings
from models.serp_models import SerpResult

logger = logging.getLogger(__name__)


def _mock_serp(keyword: str) -> List[SerpResult]:
    """APIキーがない場合などに使う MISUMI / MonotaRO モック。"""
    return [
        SerpResult(
            rank=1,
            title=f"MISUMI 検索結果: {keyword}",
            url=f"https://jp.misumi-ec.com/vona2/result/?Keyword={keyword}",
            snippet=f"MISUMI で {keyword} を検索した結果ページです。",
        ),
        SerpResult(
            rank=2,
            title=f"MonotaRO 検索結果: {keyword}",
            url=f"https://www.monotaro.com/s/q/{keyword}/",
            snippet=f"MonotaRO で {keyword} を検索した結果ページです。",
        ),
    ]


def fetch_serp_google(keyword: str, limit: int = 5) -> List[SerpResult]:
    """Google Custom Search JSON API を使って SERP を取得する。"""
    api_key = settings.google_search_api_key
    cx = settings.google_search_cx

    if not api_key or not cx:
        logger.warning("Google Search APIキーまたはCXが設定されていないためモックを使用します")
        return _mock_serp(keyword)

    params = {
        "key": api_key,
        "cx": cx,
        "q": keyword,
        "num": min(limit, 10),
        "hl": "ja",
    }
    resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: List[SerpResult] = []
    for rank, item in enumerate(data.get("items", []), start=1):
        results.append(
            SerpResult(
                rank=rank,
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", "") or item.get("title", ""),
            )
        )
        if len(results) >= limit:
            break

    if not results:
        # 何も取れなかったときはモックで補完
        return _mock_serp(keyword)

    return results
