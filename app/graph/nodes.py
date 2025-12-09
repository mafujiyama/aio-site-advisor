# app/graph/nodes.py

import logging
from datetime import datetime

from app.graph.lg_state import GraphState
from agents.keyword_planner_agent import plan_keywords
from agents.serp_agent import fetch_serp_for_keyword
from agents.parser_agent import parse_sites_for_keyword
from agents.analyzer_agent import analyze_keyword

logger = logging.getLogger(__name__)


def _log_progress(state: GraphState, node_name: str, message: str) -> GraphState:
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] [{node_name}] {message}"
    logger.info(line)
    # progress_messages にも追加
    state.progress_messages.append(line)
    state.current_node = node_name
    return state


def keyword_planner_node(state: GraphState) -> GraphState:
    state = _log_progress(state, "keyword_planner", "start: generating keyword plan")
    plan = plan_keywords(seed_keyword=state.seed_keyword, site_profile=state.site_profile)
    state.keyword_plan = plan
    state = _log_progress(
        state,
        "keyword_planner",
        f"done: generated {len(plan.items)} keyword candidates",
    )
    return state


def serp_node(state: GraphState) -> GraphState:
    state = _log_progress(state, "serp", "start: fetching SERP for top keywords")

    if not state.keyword_plan:
        return _log_progress(state, "serp", "skip: keyword_plan is None")

    # 上位3〜5件くらいだけ
    for item in state.keyword_plan.top_keywords(limit=5):
        results = fetch_serp_for_keyword(item.keyword, limit=5)
        state.serp_results[item.keyword] = results

    state = _log_progress(
        state,
        "serp",
        f"done: fetched SERP for {len(state.serp_results)} keywords",
    )
    return state


def parser_node(state: GraphState) -> GraphState:
    state = _log_progress(state, "parser", "start: parsing HTML & building structures")

    for kw, serp_list in state.serp_results.items():
        structures = parse_sites_for_keyword(kw, serp_list)
        state.site_structures[kw] = structures

    state = _log_progress(
        state,
        "parser",
        f"done: parsed structures for {len(state.site_structures)} keywords",
    )
    return state


def analyzer_node(state: GraphState) -> GraphState:
    state = _log_progress(state, "analyzer", "start: analyzing structures")

    for kw, structures in state.site_structures.items():
        state.analysis[kw] = analyze_keyword(kw, structures)

    state = _log_progress(
        state,
        "analyzer",
        f"done: built analysis for {len(state.analysis)} keywords",
    )
    return state
