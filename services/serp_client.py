# services/serp_client.py

from typing import List
from urllib.parse import quote

from models.serp_models import SerpResult


def search_serp_mock(query: str, limit: int = 5) -> List[SerpResult]:
    """
    開発用の簡易 SERP モック。
    - 1件目: MISUMI の検索結果ページ
    - 2件目: MonotaRO の検索結果ページ
    - 3件目以降: ダミーの example.com
    ※ limit が 2 以下なら、実アクセスは最大2件。
    """

    results: List[SerpResult] = []

    # 1: MISUMI 検索結果
    misumi_url = f"https://jp.misumi-ec.com/vona2/result/?Keyword={quote(query)}"
    results.append(
        SerpResult(
            rank=1,
            title=f"MISUMI 検索結果: {query}",
            url=misumi_url,
            snippet=f"MISUMI で {query} を検索した結果ページです。",
        )
    )

    if limit == 1:
        return results

    # 2: MonotaRO 検索結果
    monotaro_url = f"https://www.monotaro.com/s/q/{quote(query)}/"
    results.append(
        SerpResult(
            rank=2,
            title=f"MonotaRO 検索結果: {query}",
            url=monotaro_url,
            snippet=f"MonotaRO で {query} を検索した結果ページです。",
        )
    )

    # 3件目以降はダミー
    for i in range(3, limit + 1):
        results.append(
            SerpResult(
                rank=i,
                title=f"{query} に関するサンプルタイトル {i}",
                url=f"https://example.com/{query}/sample-{i}",
                snippet=f"{query} に関するサンプルスニペット {i} です。",
            )
        )

    return results
