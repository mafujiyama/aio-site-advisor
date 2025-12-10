# app/graph/nodes.py

from __future__ import annotations

import logging
from typing import Dict, List

from app.graph.lg_state import GraphState
from agents.keyword_planner_agent import plan_keywords
from agents.serp_agent import fetch_serp_for_keyword
from agents.parser_agent import parse_sites_for_keyword
from agents.analyzer_agent import analyze_for_graph

from models.keyword_models import KeywordPlan
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis

# ---------------------------------------------------------
# ロガー設定
# ---------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------
# 軽量化パラメータ（ここを変えれば負荷を調整できる）
# ---------------------------------------------------------
MAX_ANALYZE_KEYWORDS = 2        # SERP まで取りに行くキーワード数（元: 10）
MAX_SERP_RESULTS_PER_KEYWORD = 3  # 1キーワードあたりの SERP 件数（元: 10）


def _log_progress(state: GraphState, node: str, message: str) -> GraphState:
    """
    LangGraph 用の進捗ログを state に積むユーティリティ。
    state は dict (GraphState) として扱う。
    """
    line = f"[{node}] {message}"

    messages: List[str] = list(state.get("progress_messages", []))
    messages.append(line)

    state["progress_messages"] = messages
    state["current_node"] = node

    logger.info(line)
    return state


# ---------------------------------------------------------
# Keyword Planner ノード
# ---------------------------------------------------------

def keyword_planner_node(state: GraphState) -> GraphState:
    """
    KeywordPlanner ノード:
    seed_keyword / site_profile から KeywordPlan を生成して state に詰める。
    """
    state = _log_progress(state, "keyword_planner", "start: generating keyword plan")

    seed_keyword = state.get("seed_keyword")
    site_profile = state.get("site_profile")

    logger.info(
        "[keyword_planner_node] seed_keyword=%s site_profile=%s",
        seed_keyword,
        "YES" if site_profile else "NO",
    )

    plan = plan_keywords(
        seed_keyword=seed_keyword,
        site_profile=site_profile,
    )
    state["keyword_plan"] = plan

    logger.info(
        "[keyword_planner_node] generated items=%d",
        len(plan.items if plan and plan.items else []),
    )

    state = _log_progress(state, "keyword_planner", "done: keyword plan generated")
    return state


# ---------------------------------------------------------
# SERP ノード
# ---------------------------------------------------------

def serp_node(state: GraphState) -> GraphState:
    """
    KeywordPlanner で生成されたキーワードのうち
    上位 N 件に対して SERP を取得するノード。

    負荷軽減のため:
      - キーワード数: MAX_ANALYZE_KEYWORDS
      - 各キーワードの SERP 件数: MAX_SERP_RESULTS_PER_KEYWORD
    """
    state = _log_progress(state, "serp", "start: fetch SERP for top keywords")

    keyword_plan: KeywordPlan = state.get("keyword_plan")
    if not keyword_plan:
        logger.warning("[serp_node] keyword_plan is None -> skip")
        state = _log_progress(state, "serp", "skipped: keyword_plan is None")
        return state

    serp_results: Dict[str, List[SerpResult]] = {}

    # キーワード側：priority の高い順で MAX_ANALYZE_KEYWORDS に制限
    try:
        target_keywords = list(keyword_plan.top_keywords(limit=MAX_ANALYZE_KEYWORDS))
    except AttributeError:
        items = keyword_plan.items or []
        items_sorted = sorted(
            items,
            key=lambda it: (it.priority or 0),
            reverse=True,
        )
        target_keywords = items_sorted[:MAX_ANALYZE_KEYWORDS]

    logger.info(
        "[serp_node] target_keywords=%s",
        [k.keyword for k in target_keywords],
    )

    for kw_item in target_keywords:
        k = kw_item.keyword
        try:
            results = fetch_serp_for_keyword(k, limit=MAX_SERP_RESULTS_PER_KEYWORD)
            logger.info(
                "[serp_node] keyword=%s results=%d",
                k,
                len(results or []),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("[serp_node] error keyword=%s error=%s", k, e)
            results = []

        # 念のため limit でもう一度絞っておく
        serp_results[k] = (results or [])[:MAX_SERP_RESULTS_PER_KEYWORD]

    state["serp_results"] = serp_results

    state = _log_progress(
        state,
        "serp",
        f"done: fetched SERP for {len(serp_results)} keywords "
        f"(each up to {MAX_SERP_RESULTS_PER_KEYWORD} results)",
    )
    return state


# ---------------------------------------------------------
# Parser ノード
# ---------------------------------------------------------

def parser_node(state: GraphState) -> GraphState:
    """
    Parser ノード:
    SERP 結果の URL 群に対して HTML を取得し、SiteStructure に変換する。
    """
    state = _log_progress(state, "parser", "start: parsing HTML for SERP URLs")

    serp_results: Dict[str, List[SerpResult]] = state.get("serp_results", {}) or {}
    site_structures: Dict[str, List[SiteStructure]] = {}

    if not serp_results:
        logger.warning("[parser_node] serp_results is empty -> skip parsing")

    for kw, results in serp_results.items():
        logger.info(
            "[parser_node] keyword=%s serp_count=%d",
            kw,
            len(results or []),
        )
        try:
            pages = parse_sites_for_keyword(kw, results or [])
            site_structures[kw] = pages
            logger.info(
                "[parser_node] keyword=%s parsed_pages=%d",
                kw,
                len(pages or []),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("[parser_node] error keyword=%s error=%s", kw, e)
            site_structures[kw] = []

    state["site_structures"] = site_structures
    state = _log_progress(state, "parser", "done: parsed site structures")
    return state


# ---------------------------------------------------------
# Analyzer ノード
# ---------------------------------------------------------

def analyzer_node(state: GraphState) -> GraphState:
    """
    Analyzer ノード:
    site_structures + keyword_plan からキーワード構造分析を実施。
    """
    state = _log_progress(state, "analyzer", "start: analyzing structures")

    plan: KeywordPlan = state.get("keyword_plan")
    site_structures: Dict[str, List[SiteStructure]] = state.get("site_structures", {}) or {}

    if not plan:
        logger.warning("[analyzer_node] keyword_plan is None -> skip")
        state = _log_progress(state, "analyzer", "skipped: keyword_plan is None")
        return state

    if not site_structures:
        logger.warning("[analyzer_node] site_structures is empty -> skip")
        state = _log_progress(state, "analyzer", "skipped: site_structures is empty")
        return state

    logger.info(
        "[analyzer_node] site_structures_keywords=%s",
        list(site_structures.keys()),
    )

    analysis: Dict[str, KeywordStructureAnalysis] = analyze_for_graph(
        site_structures,
        plan,
    )
    state["analysis"] = analysis

    logger.info(
        "[analyzer_node] analysis_keywords=%d",
        len(analysis or {}),
    )

    state = _log_progress(state, "analyzer", "done: analysis complete")
    return state
