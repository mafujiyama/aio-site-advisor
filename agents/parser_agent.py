# agents/parser_agent.py

from typing import List, Optional
import logging

from models.serp_models import SerpResult
from models.site_models import SiteStructure
from services.crawler import fetch_html
from services.html_parser import parse_html

logger = logging.getLogger(__name__)


def parse_sites_from_serp(serp_results: List[SerpResult]) -> List[SiteStructure]:
    """
    SERP で得た URL リストに対して HTML を取得し、SiteStructure に変換する。
    失敗した URL については、SERP 情報から簡易的な構造を生成する（空にはしない）。

    将来的な拡張ポイント：
    - 見出し階層の tree 構造化
    - TF-IDF 用の token 化
    - LLM に渡す summary 作成
    - コンテンツスコアリング用のメタ情報追加
    """
    structures: List[SiteStructure] = []

    for res in serp_results:
        url = res.url
        try:
            logger.info(f"[parser_agent] Fetching HTML: {url}")

            # ----- 1) HTML を取得 -----
            html = fetch_html(url)

            # ----- 2) BeautifulSoup などで構造化 -----
            structure = parse_html(url, html)
            structures.append(structure)

            logger.info(
                f"[parser_agent] Parsed successfully: {url} "
                f"(title={structure.title}, words={structure.word_count})"
            )

        except Exception as e:
            # ----- 3) フォールバック -----
            logger.warning(f"[parser_agent] Error for {url}: {e}")

            fallback = SiteStructure(
                url=url,
                title=res.title,
                meta_description=res.snippet,
                h1_list=[],
                headings=[],
                main_text=res.snippet or "",
                word_count=len((res.snippet or "").split()),
            )
            structures.append(fallback)

            logger.info(
                f"[parser_agent] Fallback used for URL: {url} "
                f"(title={fallback.title}, words={fallback.word_count})"
            )

    return structures


def parse_sites_for_keyword(
    keyword_or_serp: object,
    maybe_serp: Optional[List[SerpResult]] = None,
) -> List[SiteStructure]:
    """
    LangGraph ノード側との互換用ラッパ。

    想定される呼び出しパターン：
      - parse_sites_for_keyword(serp_results)
      - parse_sites_for_keyword(keyword, serp_results)

    どちらの場合でも最終的に parse_sites_from_serp() を呼び出す。
    """
    # パターン1: parse_sites_for_keyword(serp_results)
    if maybe_serp is None:
        serp_results = keyword_or_serp  # type: ignore[assignment]
    else:
        # パターン2: parse_sites_for_keyword(keyword, serp_results)
        serp_results = maybe_serp

    return parse_sites_from_serp(serp_results)  # type: ignore[arg-type]
