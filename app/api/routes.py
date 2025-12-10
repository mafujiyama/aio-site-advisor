# app/api/routes.py

from typing import Optional, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from app.graph.workflow import run_simple_analysis
from app.graph.lg_workflow import graph_app

from agents.keyword_planner_agent import plan_keywords as plan_keywords_agent

from models.keyword_models import KeywordPlan
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis

router = APIRouter()


# ========= リクエストモデル =========

class KeywordPlanRequest(BaseModel):
    seed_keyword: str
    site_profile: Optional[dict] = None


class SimpleAnalyzeRequest(BaseModel):
    seed_keyword: str
    site_profile: Optional[dict] = None


class AnalyzeLgRequest(BaseModel):
    seed_keyword: str
    site_profile: Optional[dict] = None


# ========= レスポンスモデル =========

class KeywordPlanResponse(BaseModel):
    seed_keyword: str
    keyword_plan: KeywordPlan


class SimpleAnalyzeResponse(BaseModel):
    seed_keyword: str
    keyword_plan: KeywordPlan
    serp_results: Dict[str, List[SerpResult]]
    site_structures: Dict[str, List[SiteStructure]]


class AnalyzeLgResponse(BaseModel):
    """
    LangGraph を使ったマルチステップ分析のレスポンス。
    Analyzer ノードの結果 (analysis) も含める。
    """
    seed_keyword: str
    keyword_plan: KeywordPlan
    serp_results: Dict[str, List[SerpResult]]
    site_structures: Dict[str, List[SiteStructure]]
    analysis: Dict[str, KeywordStructureAnalysis] = {}


# ========= エンドポイント =========

@router.post("/plan-keywords", response_model=KeywordPlanResponse)
def plan_keywords_endpoint(body: KeywordPlanRequest) -> KeywordPlanResponse:
    """
    KeywordPlanner エージェント単体テスト用エンドポイント。
    """
    plan: KeywordPlan = plan_keywords_agent(
        seed_keyword=body.seed_keyword,
        site_profile=body.site_profile,
    )

    return KeywordPlanResponse(
        seed_keyword=body.seed_keyword,
        keyword_plan=plan,
    )


@router.post("/analyze-simple", response_model=SimpleAnalyzeResponse)
def analyze_simple_endpoint(body: SimpleAnalyzeRequest) -> SimpleAnalyzeResponse:
    """
    旧ワークフロー（LangGraphなし）の簡易版分析。
    """
    state = run_simple_analysis(
        seed_keyword=body.seed_keyword,
        site_profile=body.site_profile,
    )
    if not state.keyword_plan:
        raise RuntimeError("keyword_plan が生成されていません")

    return SimpleAnalyzeResponse(
        seed_keyword=state.seed_keyword,
        keyword_plan=state.keyword_plan,
        serp_results=state.serp_results,
        site_structures=state.site_structures,
    )


@router.post("/analyze-lg", response_model=AnalyzeLgResponse)
def analyze_lg_endpoint(body: AnalyzeLgRequest) -> AnalyzeLgResponse:
    """
    LangGraph を用いたマルチステップ分析エンドポイント。
    KeywordPlanner → SERP → Parser → Analyzer の結果を返す。
    """
    # ★ LangGraph 用の state は dict ベース（GraphState）で始める
    initial_state = {
        "seed_keyword": body.seed_keyword,
        "site_profile": body.site_profile,
    }

    final_state = graph_app.invoke(initial_state)

    return AnalyzeLgResponse(
        seed_keyword=final_state.get("seed_keyword", body.seed_keyword),
        keyword_plan=final_state["keyword_plan"],
        serp_results=final_state.get("serp_results", {}),
        site_structures=final_state.get("site_structures", {}),
        analysis=final_state.get("analysis", {}),
    )
