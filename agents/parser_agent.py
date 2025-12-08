# agents/parser_agent.py

from typing import List

from models.serp_models import SerpResult
from models.site_models import SiteStructure, Heading
from services.crawler import fetch_html
from services.html_parser import parse_html


def parse_sites_from_serp(serp_results: List[SerpResult]) -> List[SiteStructure]:
    """
    SERPで得たURLリストに対して、
    実際にHTMLを取りに行き、SiteStructureに変換する。
    もしHTML取得やパースに失敗した場合は、
    SERP情報からの簡易ダミー構造を返す（空にはしない）。
    """
    structures: List[SiteStructure] = []

    for res in serp_results:
        try:
            # まずは本命：実HTMLを取りに行く
            html = fetch_html(res.url)
            structure = parse_html(res.url, html)
            structures.append(structure)
        except Exception as e:
            # ここに来る＝HTTPエラー / TLS / パースエラーなど
            print(f"[parser_agent] error for {res.url}: {e}")

            # フォールバック：SERPの title / snippet から最低限の構造を作る
            fallback = SiteStructure(
                url=res.url,
                title=res.title,
                meta_description=res.snippet,
                h1_list=[],
                headings=[],
                main_text=res.snippet or "",
                word_count=len((res.snippet or "").split()),
            )
            structures.append(fallback)

    return structures
