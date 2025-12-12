# app/graph/lg_state.py
from __future__ import annotations

from typing import Any, Dict, Optional


class GraphState(Dict[str, Any]):
    """
    LangGraph 風の「状態」コンテナ。
    実体はただの dict だが、型ヒントとして分かりやすくするためのラッパ。
    """
    pass


def create_initial_state(
    seed_keyword: str,
    site_profile: Optional[str] = None,
) -> GraphState:
    """
    ワークフロー開始時の初期 state を作成。
    """
    state: GraphState = GraphState()
    state["seed_keyword"] = seed_keyword
    state["site_profile"] = site_profile
    state["progress_messages"] = []  # 各ノードからのログ的メッセージ
    state["current_node"] = None
    return state
