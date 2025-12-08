# app/graph/nodes.py

from typing import Dict, List
from langchain_core.runnables import RunnableConfig

from app.graph.lg_state import GraphState
from agents.keyword_planner_agent import plan_keywords
from agents.serp_agent import fetch_serp_for_keyword
from agents.parser_agent import parse_sites_from_serp
from agents.analyzer_agent import analyze_for_graph
from models.serp_models import SerpResult
from models.site_models import SiteStructure


# テストしやすいように少なめ
TOP_N_KEYWORDS = 1   # 上位1キーワードだけ
SERP_LIMIT = 2       # SERP上位2件だけ


def keyword_planner_node(state: GraphState, config: RunnableConfig) -> Dict:
    """
    キーワード設計エージェントノード
    seed_keyword と site_profile から KeywordPlan を作る
    """
    seed_keyword = state["seed_keyword"]
    site_profile = state.get("site_profile")

    keyword_plan = plan_keywords(seed_keyword, site_profile)

    return {
        "keyword_plan": keyword_plan
    }


def serp_node(state: GraphState, config: RunnableConfig) -> Dict:
    """
    KeywordPlan から上位キーワードを選び、SERP（モック or 実）を取得するノード
    """
    keyword_plan = state.get("keyword_plan")
    if keyword_plan is None:
        raise RuntimeError("keyword_plan が state にありません")

    serp_results: Dict[str, List[SerpResult]] = {}

    for kw in keyword_plan.top_keywords(limit=TOP_N_KEYWORDS):
        results = fetch_serp_for_keyword(kw.keyword, limit=SERP_LIMIT)
        serp_results[kw.keyword] = results

    return {
        "serp_results": serp_results
    }


def parser_node(state: GraphState, config: RunnableConfig) -> Dict:
    """
    SERP結果のURLごとにHTMLを取得し、SiteStructure に変換するノード
    """
    serp_results = state.get("serp_results") or {}

    site_structures: Dict[str, List[SiteStructure]] = {}

    for keyword, results in serp_results.items():
        structures = parse_sites_from_serp(results)
        site_structures[keyword] = structures

    return {
        "site_structures": site_structures
    }


def analyzer_node(state: GraphState, config: RunnableConfig) -> Dict:
    """
    Parser の出力（site_structures）と keyword_plan をもとに
    ページ構造を数値化するノード
    """
    site_structures = state.get("site_structures") or {}
    keyword_plan = state.get("keyword_plan")
    if not keyword_plan:
        # keyword_plan がない場合は何もしない
        return {}

    analysis = analyze_for_graph(site_structures, keyword_plan)

    # ★ ここで必ず key を返す（空でも）
    return {
        "analysis": analysis
    }
