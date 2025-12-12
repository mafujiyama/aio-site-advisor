# app/api/routes.py
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from agents.keyword_planner_agent import plan_keywords
from app.graph.lg_workflow import run_workflow
from models.keyword_models import KeywordPlan
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis
from models.strategy_models import StrategySummary

logger = logging.getLogger(__name__)

router = APIRouter()


# --------- Request / Response モデル ---------


class PlanKeywordsRequest(BaseModel):
    seed_keyword: str
    site_profile: Optional[str] = None


class AnalyzeLGRequest(BaseModel):
    seed_keyword: str
    site_profile: Optional[str] = None


class AnalyzeLGResponse(BaseModel):
    seed_keyword: str
    keyword_plan: KeywordPlan
    serp_results: Dict[str, List[SerpResult]]
    site_structures: Dict[str, List[SiteStructure]]
    analysis: Dict[str, KeywordStructureAnalysis]
    strategy: StrategySummary
    progress_messages: List[str] = []


# --------- エンドポイント ---------


@router.post("/plan-keywords", response_model=KeywordPlan)
def api_plan_keywords(payload: PlanKeywordsRequest) -> KeywordPlan:
    """
    seed_keyword + 任意の site_profile から KeywordPlan を返すシンプルAPI。
    LLM が正常に動いているか確認する用。
    """
    logger.info(
        "[api.plan-keywords] seed_keyword=%s site_profile=%s",
        payload.seed_keyword,
        "YES" if payload.site_profile else "NO",
    )
    plan = plan_keywords(
        seed_keyword=payload.seed_keyword,
        site_profile=payload.site_profile,
    )
    return plan


@router.post("/analyze-lg", response_model=AnalyzeLGResponse)
def api_analyze_lg(payload: AnalyzeLGRequest) -> AnalyzeLGResponse:
    """
    LangGraph 風ワークフローをまとめて実行するメインAPI。

    1) KeywordPlanner (LLM)
    2) SERP 取得
    3) HTML パース → SiteStructure
    4) Analyzer で構造分析
    5) Strategist (LLM) で戦略サマリ生成
    """
    logger.info(
        "[api.analyze-lg] start seed_keyword=%s site_profile=%s",
        payload.seed_keyword,
        "YES" if payload.site_profile else "NO",
    )

    state = run_workflow(
        seed_keyword=payload.seed_keyword,
        site_profile=payload.site_profile,
    )

    logger.info(
        "[api.analyze-lg] done seed_keyword=%s nodes=%s",
        payload.seed_keyword,
        state.get("current_node"),
    )

    return AnalyzeLGResponse(
        seed_keyword=state["seed_keyword"],
        keyword_plan=state["keyword_plan"],
        serp_results=state.get("serp_results", {}),
        site_structures=state.get("site_structures", {}),
        analysis=state.get("analysis", {}),
        strategy=state.get("strategy"),
        progress_messages=state.get("progress_messages", []),
    )
