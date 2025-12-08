# agents/analyzer_agent.py

from typing import Dict, List
from urllib.parse import urlparse

from models.site_models import SiteStructure
from models.analysis_models import PageStructureMetrics, KeywordStructureAnalysis
from models.keyword_models import KeywordPlan


def _count_term_freq(text: str, keyword: str) -> int:
    if not text:
        return 0
    return text.count(keyword)


def analyze_keyword_structures(
    keyword: str,
    pages: List[SiteStructure],
) -> KeywordStructureAnalysis:
    metrics_list: List[PageStructureMetrics] = []

    for p in pages:
        parsed = urlparse(p.url)
        domain = parsed.netloc

        h2_count = sum(1 for h in p.headings if h.level == 2)
        h3_count = sum(1 for h in p.headings if h.level == 3)

        title = p.title or ""
        meta_desc = p.meta_description or ""
        body_text = p.main_text or ""
        h1_joined = " ".join(p.h1_list or [])

        metrics = PageStructureMetrics(
            url=p.url,
            domain=domain,
            title_length=len(title),
            meta_description_length=len(meta_desc),
            h1_count=len(p.h1_list or []),
            h2_count=h2_count,
            h3_count=h3_count,
            word_count=p.word_count or 0,
            keyword_in_title=(keyword in title),
            keyword_in_h1=(keyword in h1_joined),
            keyword_term_freq=_count_term_freq(body_text, keyword),
        )
        metrics_list.append(metrics)

    return KeywordStructureAnalysis(keyword=keyword, pages=metrics_list)


def analyze_for_graph(
    site_structures: Dict[str, List[SiteStructure]],
    keyword_plan: KeywordPlan,
) -> Dict[str, KeywordStructureAnalysis]:
    """
    LangGraph用: site_structures + keyword_plan から
    キーワードごとの構造分析結果を Dict で返す。
    今は TOP 1キーワードだけ分析。
    """
    result: Dict[str, KeywordStructureAnalysis] = {}

    for kw_item in keyword_plan.top_keywords(limit=1):
        kw = kw_item.keyword
        pages = site_structures.get(kw, [])
        if not pages:
            continue
        result[kw] = analyze_keyword_structures(kw, pages)

    # ★ 必ず dict を返す（空でも）
    return result
