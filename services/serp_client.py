# services/serp_client.py
from __future__ import annotations

import logging
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.config import settings
from models.serp_models import SerpResult

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_HTML_URL = "https://www.google.com/search"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

# ブラウザっぽい UA（HTML スクレイピングで使用）
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ------------------------------------------------------------------
# ① Google CSE API 版（正式推奨ルート）
# ------------------------------------------------------------------
def fetch_serp_cse(keyword: str, limit: int = 10) -> List[SerpResult]:
    """
    Google Custom Search JSON API (CSE) を使って SERP を取得する正式ルート。

    - settings.google_search_api_key / settings.google_search_cx が必須
    - エラー時・空レスポンス時は [] を返す
    - ログにリクエスト内容とレスポンスの一部を出力してデバッグしやすくする
    """
    api_key = settings.google_search_api_key
    cx = settings.google_search_cx

    if not api_key or not cx:
        logger.warning(
            "[CSE] api_key or cx is not set. api_key=%s cx=%s",
            bool(api_key),
            bool(cx),
        )
        return []

    params = {
        "key": api_key,
        "cx": cx,
        "q": keyword,
        "num": min(limit, 10),  # CSE の上限は 10
        "hl": "ja",
    }

    logger.info("[CSE] Request start: keyword=%s params=%s", keyword, params)

    try:
        resp = requests.get(GOOGLE_CSE_URL, params=params, timeout=10)
    except Exception as e:
        logger.exception("[CSE] Request failed: %s", e)
        return []

    raw_text = resp.text
    logger.info(
        "[CSE] Response: status=%s, length=%s, body_snippet=%s",
        resp.status_code,
        len(raw_text),
        raw_text[:2000],
    )

    try:
        resp.raise_for_status()
    except Exception:
        # ★ エラー時の中身をちゃんと見るためのログ
        logger.error(
            "[CSE] Non-200 status: %s body=%s",
            resp.status_code,
            raw_text[:2000],
        )
        return []

    # ここからは 2xx の場合
    data = resp.json()

    items = data.get("items") or []
    if not items:
        logger.warning(
            "[CSE] items is empty. keys=%s error=%s",
            list(data.keys()),
            data.get("error"),
        )
        return []

    results: List[SerpResult] = []
    for rank, item in enumerate(items, start=1):
        results.append(
            SerpResult(
                rank=rank,
                title=item.get("title", "") or "",
                url=item.get("link", "") or "",
                snippet=item.get("snippet", "") or item.get("title", "") or "",
            )
        )
        if len(results) >= limit:
            break

    logger.info("[CSE] Parsed results count=%s", len(results))
    return results



# ------------------------------------------------------------------
# ③ 既存インターフェイス（SERP Agent がこれを呼ぶ）
# ------------------------------------------------------------------
def fetch_serp_google(keyword: str, limit: int = 10) -> List[SerpResult]:
    """
    既存の呼び出しインターフェースを維持しつつ、
    “正式版：CSE” を返すように変更。

    ※ HTML 版を使いたい場合は fetch_serp_for_keyword_html() を直接呼ぶこと
    """
    return fetch_serp_cse(keyword, limit=limit)
