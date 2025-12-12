# app/graph/nodes.py
from __future__ import annotations

import logging
from typing import Dict, List

from app.graph.lg_state import GraphState
from agents.keyword_planner_agent import plan_keywords
from agents.serp_agent import fetch_serp_for_keyword
from agents.parser_agent import parse_sites_for_keyword
from agents.analyzer_agent import analyze_for_graph
from agents.strategist_agent import build_strategy

from models.keyword_models import KeywordPlan
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis
from models.strategy_models import StrategySummary

logger = logging.getLogger(__name__)


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


# ---------- Keyword Planner ノード ----------


def keyword_planner_node(state: GraphState) -> GraphState:
    """
    KeywordPlanner ノード:
    seed_keyword / site_profile から KeywordPlan を生成して state に詰める。
    """
    state = _log_progress(state, "keyword_planner", "start: generating keyword plan")

    seed = state["seed_keyword"]
    site_profile = state.get("site_profile")

    logger.info(
        "[keyword_planner_node] seed_keyword=%s site_profile=%s",
        seed,
        "YES" if site_profile else "NO",
    )

    plan = plan_keywords(
        seed_keyword=seed,
        site_profile=site_profile,
    )
    state["keyword_plan"] = plan

    logger.info(
        "[keyword_planner_node] generated items=%s",
        len(plan.items) if hasattr(plan, "items") else "N/A",
    )

    state = _log_progress(state, "keyword_planner", "done: keyword plan generated")
    return state


# ---------- SERP ノード ----------


# CSE 無料枠を考慮してデフォルトはかなり絞る
MAX_ANALYZE_KEYWORDS = 2
MAX_SERP_RESULTS_PER_KEYWORD = 3


def serp_node(state: GraphState) -> GraphState:
    """
    KeywordPlanner で生成されたキーワードのうち
    上位 N 件に対して SERP を取得するノード。

    ※ CSE の無料枠を考慮して N をかなり小さくしている。
    """
    state = _log_progress(state, "serp", "start: fetch SERP for top keywords")

    keyword_plan: KeywordPlan = state["keyword_plan"]
    serp_results: Dict[str, List[SerpResult]] = {}

    target_keywords = [kw_item.keyword for kw_item in keyword_plan.top_keywords(limit=MAX_ANALYZE_KEYWORDS)]

    logger.info("[serp_node] target_keywords=%s", target_keywords)

    for k in target_keywords:
        results = fetch_serp_for_keyword(k, limit=MAX_SERP_RESULTS_PER_KEYWORD)
        serp_results[k] = results
        logger.info(
            "[serp_node] keyword=%s results=%s",
            k,
            len(results),
        )

    state["serp_results"] = serp_results

    state = _log_progress(
        state,
        "serp",
        f"done: fetched SERP for {len(serp_results)} keywords (each up to {MAX_SERP_RESULTS_PER_KEYWORD} results)",
    )
    return state


# ---------- Parser ノード ----------


def parser_node(state: GraphState) -> GraphState:
    """
    Parser ノード:
    SERP 結果の URL 群に対して HTML を取得し、SiteStructure に変換する。
    """
    state = _log_progress(state, "parser", "start: parsing HTML for SERP URLs")

    serp_results: Dict[str, List[SerpResult]] = state.get("serp_results", {})
    site_structures: Dict[str, List[SiteStructure]] = {}

    for kw, results in serp_results.items():
        logger.info("[parser_node] keyword=%s serp_count=%s", kw, len(results))
        pages = parse_sites_for_keyword(kw, results)
        site_structures[kw] = pages
        logger.info("[parser_node] keyword=%s parsed_pages=%s", kw, len(pages))

    state["site_structures"] = site_structures
    state = _log_progress(state, "parser", "done: parsed site structures")
    return state


# ---------- Analyzer ノード ----------


def analyzer_node(state: GraphState) -> GraphState:
    """
    Analyzer ノード:
    site_structures + keyword_plan からキーワード構造分析を実施。
    """
    state = _log_progress(state, "analyzer", "start: analyzing structures")

    plan: KeywordPlan = state["keyword_plan"]
    site_structures: Dict[str, List[SiteStructure]] = state.get("site_structures", {})

    logger.info(
        "[analyzer_node] site_structures_keywords=%s",
        list(site_structures.keys()),
    )

    analysis: Dict[str, KeywordStructureAnalysis] = analyze_for_graph(
        site_structures=site_structures,
        keyword_plan=plan,
    )
    state["analysis"] = analysis

    logger.info(
        "[analyzer_node] analysis_keywords=%s",
        len(analysis),
    )

    state = _log_progress(state, "analyzer", "done: analysis complete")
    return state


# ---------- Strategist ノード（新規 LLM エージェント） ----------


def strategist_node(state: GraphState) -> GraphState:
    """
    Strategist ノード:
    KeywordPlan + 構造分析結果 + site_profile を元に
    LLM で戦略サマリを生成する。
    """
    state = _log_progress(state, "strategist", "start: building strategy")

    seed_keyword: str = state["seed_keyword"]
    keyword_plan: KeywordPlan = state.get("keyword_plan")
    analysis: Dict[str, KeywordStructureAnalysis] = state.get("analysis", {})
    site_profile = state.get("site_profile")

    logger.info(
        "[strategist_node] seed_keyword=%s plan_items=%s analysis_keywords=%s",
        seed_keyword,
        len(keyword_plan.items) if hasattr(keyword_plan, "items") else "N/A",
        len(analysis),
    )

    strategy: StrategySummary = build_strategy(
        seed_keyword=seed_keyword,
        keyword_plan=keyword_plan,
        analysis=analysis,
        site_profile=site_profile,
    )

    state["strategy"] = strategy

    state = _log_progress(state, "strategist", "done: strategy generated")
    return state
