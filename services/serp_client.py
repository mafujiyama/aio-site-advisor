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
    params = {
        # app/config.py に定義されているフィールド名に合わせる
        "key": settings.google_search_api_key,
        "cx": settings.google_search_cx,
        "q": keyword,
        "num": min(limit, 10),
        "hl": "ja",
    }

    logger.info("[CSE] Request start: params=%s", params)

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
        logger.error("[CSE] Non-200 status: %s", resp.status_code)
        return []

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
    for idx, item in enumerate(items, start=1):
        results.append(
            SerpResult(
                rank=idx,
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            )
        )
        if len(results) >= limit:
            break

    logger.info("[CSE] Parsed SERP count=%d", len(results))
    return results



# ------------------------------------------------------------------
# ② HTML スクレイピング版（PoC 用）
# ------------------------------------------------------------------
def fetch_serp_for_keyword_html(keyword: str, limit: int = 10) -> List[SerpResult]:
    """
    Google 検索結果ページ(HTML)をスクレイピングする PoC モード。
    運用には不向きだが、動作確認用途として保持。
    """
    params = {
        "q": keyword,
        "hl": "ja",
        "num": min(limit, 10),
    }

    logger.info("[HTML] Request start: %s", params)

    try:
        resp = requests.get(
            GOOGLE_SEARCH_HTML_URL,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("[HTML] Google search request failed: %s", e)
        return []

    html = resp.text

    # bot 判定
    if "Our systems have detected unusual traffic" in html:
        logger.warning("[HTML] Bot detected (unusual traffic)")
        return []

    soup = BeautifulSoup(html, "html.parser")

    results: List[SerpResult] = []
    for rank, g in enumerate(soup.select("div.g"), start=1):
        a_tag = g.select_one("a")
        title_tag = g.select_one("h3")

        if not a_tag or not title_tag:
            continue

        url = a_tag.get("href", "").strip()
        title = title_tag.get_text(strip=True)

        snippet_tag = (
            g.select_one("div[style*='-webkit-line-clamp']")
            or g.select_one("span")
            or g.select_one("div")
        )
        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

        if not url:
            continue

        results.append(
            SerpResult(rank=rank, title=title, url=url, snippet=snippet)
        )

        if len(results) >= limit:
            break

    logger.info("[HTML] SERP fetched keyword=%s results=%d", keyword, len(results))
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
