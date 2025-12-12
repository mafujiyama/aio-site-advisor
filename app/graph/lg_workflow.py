# app/graph/lg_workflow.py
from __future__ import annotations

import logging
from typing import Optional

from app.graph.lg_state import GraphState, create_initial_state
from app.graph import nodes

logger = logging.getLogger(__name__)


def run_workflow(
    seed_keyword: str,
    site_profile: Optional[str] = None,
) -> GraphState:
    """
    /api/analyze-lg 用のシンプルな直列ワークフロー。

    keyword_planner → serp → parser → analyzer → strategist
    """
    logger.info(
        "[lg_workflow] run_workflow start seed_keyword=%s site_profile=%s",
        seed_keyword,
        "YES" if site_profile else "NO",
    )

    state = create_initial_state(seed_keyword=seed_keyword, site_profile=site_profile)

    # 1) キーワードプランナー (LLM)
    state = nodes.keyword_planner_node(state)

    # 2) SERP 取得（現在は Google CSE 経由 or 0件フォールバック）
    state = nodes.serp_node(state)

    # 3) HTML パース → SiteStructure
    state = nodes.parser_node(state)

    # 4) 構造分析
    state = nodes.analyzer_node(state)

    # 5) 戦略サマリ（LLM） ← 新規 Strategist Agent
    state = nodes.strategist_node(state)

    logger.info(
        "[lg_workflow] run_workflow done seed_keyword=%s current_node=%s",
        seed_keyword,
        state.get("current_node"),
    )
    return state
