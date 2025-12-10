# services/serp_client.py

from __future__ import annotations

import logging
import time
from typing import List, Optional

import requests

from app.config import settings
from models.serp_models import SerpResult

logger = logging.getLogger(__name__)

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def _safe_request_with_retry(
    url: str,
    params: dict,
    timeout: int = 10,
    max_retries: int = 2,
    backoff: float = 1.5,
) -> Optional[dict]:
    """
    Google CSE 429 対策付きリクエストユーティリティ。

    - 合計試行回数 = max_retries + 1 回
      （例: max_retries=2 → 最大 3 回）
    - 429 のときだけ backoff 秒スリープしてリトライ
    """
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):  # 1〜(max_retries+1)
        try:
            resp = requests.get(url, params=params, timeout=timeout)

            if resp.status_code == 429:
                logger.warning(
                    "[serp_client] 429 Too Many Requests "
                    f"(attempt {attempt}/{total_attempts}). "
                    f"Sleeping {backoff} sec..."
                )
                # まだ次の試行があるなら待って再試行
                if attempt < total_attempts:
                    time.sleep(backoff)
                    continue
                # ここで打ち止め
                return None

            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            logger.warning(
                "[serp_client] Request error on attempt %d/%d: %s",
                attempt,
                total_attempts,
                e,
            )
            if attempt >= total_attempts:
                return None

    return None


def fetch_serp_google(keyword: str, limit: int = 10) -> List[SerpResult]:
    """
    Google Custom Search JSON API を使って SERP を取得する。

    - APIキーやCXが未設定 → 空リスト
    - 429発生 → 短いクールダウンを挟みながらリトライ
    - それでもダメなら空リスト
    """
    api_key = settings.google_search_api_key
    cx = settings.google_search_cx

    if not api_key or not cx:
        logger.warning(
            "[serp_client] google_search_api_key / google_search_cx が未設定のため空リストを返します"
        )
        return []

    params = {
        "key": api_key,
        "cx": cx,
        "q": keyword,
        "num": min(limit, 10),  # Google CSE の上限が 10
        "hl": "ja",
    }

    data = _safe_request_with_retry(
        GOOGLE_CSE_ENDPOINT,
        params=params,
        timeout=10,
        max_retries=2,   # 429時に最大 2 回リトライ
        backoff=1.5,     # 429時の待機秒
    )

    if not data:
        logger.warning(
            "[serp_client] Failed to fetch SERP after retries keyword=%s",
            keyword,
        )
        return []

    results: List[SerpResult] = []
    for rank, item in enumerate(data.get("items", []), start=1):
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

    return results
