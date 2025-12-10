# app/graph/workflow.py

from typing import Optional

from app.graph.state import WorkflowState
from agents.keyword_planner_agent import plan_keywords
from agents.serp_agent import fetch_serp_for_keyword


def run_keyword_planning(
    seed_keyword: str,
    site_profile: Optional[dict] = None,
) -> WorkflowState:
    """
    KeywordPlanner だけを実行するシンプルなワークフロー。
    /api/plan-keywords から呼ばれる。
    """
    state = WorkflowState(seed_keyword=seed_keyword, site_profile=site_profile)

    # キーワードプラン生成（LLM or フォールバック）
    keyword_plan = plan_keywords(seed_keyword, site_profile)
    state.keyword_plan = keyword_plan

    # 便宜的に最優先キーワードを1件だけ current_keyword に設定
    top_list = keyword_plan.top_keywords(limit=1)
    if top_list:
        state.current_keyword = top_list[0]

    return state


def run_simple_analysis(
    seed_keyword: str,
    site_profile: Optional[dict] = None,
    top_n_keywords: int = 10,  # ★ デフォルトを 10 に
    serp_limit: int = 10,      # ★ SERP も 10 件/キーワード
) -> WorkflowState:
    """
    ① キーワードプラン → ② 上位キーワードごとに SERP を取得する簡易ワークフロー。
    /api/analyze-simple から呼ばれる。

    ※ plan_keywords() は LLM＋フォールバック実装のため、
       ここも自動的に LLM 対応済み。
    """
    state = WorkflowState(seed_keyword=seed_keyword, site_profile=site_profile)

    # 1) キーワードプラン
    keyword_plan = plan_keywords(seed_keyword, site_profile)
    state.keyword_plan = keyword_plan

    # 2) 上位 N キーワードに対して SERP を取得（最大 10）
    target_keywords = keyword_plan.top_keywords(limit=top_n_keywords)

    for kw in target_keywords:
        serp_results = fetch_serp_for_keyword(kw.keyword, limit=serp_limit)
        state.serp_results[kw.keyword] = serp_results

    # 最優先キーワードを current_keyword に設定
    top_list = keyword_plan.top_keywords(limit=1)
    if top_list:
        state.current_keyword = top_list[0]

    return state
