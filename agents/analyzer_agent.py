# agents/analyzer_agent.py

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

from models.site_models import SiteStructure
from models.analysis_models import PageStructureMetrics, KeywordStructureAnalysis
from models.keyword_models import KeywordPlan

# ============================================================
# 軽量化用パラメータ
# ============================================================

# LangGraph 用の構造分析で「何個のキーワード」を対象にするか
# 今はパフォーマンス優先で 1 件だけ（必要に応じて 3,5 などに増やせる）
MAX_ANALYZE_KEYWORDS: int = 1

# 1 キーワードあたり「何ページ分」の構造指標を返すか
# サイト構造情報が増えてきたときの JSON 爆発を防ぐための上限
MAX_PAGES_PER_KEYWORD: int = 5


# ============================================================
# ユーティリティ
# ============================================================

def _count_term_freq(text: str, keyword: str) -> int:
    """本文テキスト中のキーワード出現回数をカウントする簡易関数。"""
    if not text:
        return 0
    return text.count(keyword)


def _pick_keywords_for_analysis(plan: KeywordPlan, limit: int) -> List:
    """
    構造分析の対象にするキーワードを絞り込む。

    現状の KeywordPlan は top_keywords(limit=...) を持っている前提なので、
    それをそのまま利用しつつ、将来 priority ベースのソートなどに
    差し替えやすいようにラッパ関数化している。
    """
    # 既存の挙動を踏襲：top_keywords(limit=1) を拡張した形
    # （limit は MAX_ANALYZE_KEYWORDS から渡される）
    try:
        return list(plan.top_keywords(limit=limit))
    except AttributeError:
        # 念のため top_keywords が無い場合も安全に動くようにする
        items = getattr(plan, "items", []) or []
        # priority があれば priority の高い順にする
        items_sorted = sorted(
            items,
            key=lambda it: getattr(it, "priority", 0) or 0,
            reverse=True,
        )
        return items_sorted[:limit]


# ============================================================
# メインロジック
# ============================================================

def analyze_keyword_structures(
    keyword: str,
    pages: List[SiteStructure],
) -> KeywordStructureAnalysis:
    """
    1つのキーワードに対して、関連ページ群の構造指標を集計する。

    - URL / ドメイン
    - タイトル文字数 / description 文字数
    - h1/h2/h3 の数
    - 本文の word_count
    - keyword が title / h1 に含まれるか
    - keyword の本文中出現回数

    などを PageStructureMetrics としてまとめ、
    KeywordStructureAnalysis に詰めて返す。
    """
    metrics_list: List[PageStructureMetrics] = []

    # JSON サイズ削減のため、ここで pages の長さを制限しておく
    target_pages = pages[:MAX_PAGES_PER_KEYWORD] if MAX_PAGES_PER_KEYWORD > 0 else pages

    for p in target_pages:
        parsed = urlparse(p.url)
        domain = parsed.netloc

        # headings は HeadingNode(level, text, children, ...) 想定
        h2_count = sum(1 for h in p.headings if getattr(h, "level", None) == 2)
        h3_count = sum(1 for h in p.headings if getattr(h, "level", None) == 3)

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


def analyze_keyword(keyword: str, pages: List[SiteStructure]) -> KeywordStructureAnalysis:
    """
    LangGraph の analyzer_node から呼ばれる想定のショートカット関数。

    既存の analyze_keyword_structures() をそのまま呼び出すラッパ。
    nodes.py ではこの名前を import しているため、互換性のために定義する。
    """
    return analyze_keyword_structures(keyword, pages)


def analyze_for_graph(
    site_structures: Dict[str, List[SiteStructure]],
    keyword_plan: KeywordPlan,
) -> Dict[str, KeywordStructureAnalysis]:
    """
    LangGraph用:
    site_structures + keyword_plan からキーワードごとの構造分析結果を Dict で返す。

    もともとは「TOP 1 キーワードだけ分析」だったが、
    MAX_ANALYZE_KEYWORDS を変更することで柔軟に制御できる。

    パフォーマンスを重視する場合:
        MAX_ANALYZE_KEYWORDS = 1
        MAX_PAGES_PER_KEYWORD = 3〜5 くらいが目安。
    """
    result: Dict[str, KeywordStructureAnalysis] = {}

    if not keyword_plan:
        return result

    # ★ ここで「どのキーワードを分析するか」を絞る
    target_kw_items = _pick_keywords_for_analysis(
        keyword_plan,
        limit=MAX_ANALYZE_KEYWORDS,
    )

    for kw_item in target_kw_items:
        kw = kw_item.keyword
        pages = site_structures.get(kw, [])
        if not pages:
            continue

        # analyze_keyword_structures 内でも MAX_PAGES_PER_KEYWORD をかけているが、
        # 念のためここでも slices をかけておくことで、後続処理も軽くできる。
        limited_pages = pages[:MAX_PAGES_PER_KEYWORD] if MAX_PAGES_PER_KEYWORD > 0 else pages
        result[kw] = analyze_keyword_structures(kw, limited_pages)

    # ★ 必ず dict を返す（空でも）
    return result
