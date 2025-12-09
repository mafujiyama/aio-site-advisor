# app/graph/state.py

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from models.keyword_models import KeywordPlan, KeywordItem
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis


class WorkflowState(BaseModel):
    """
    LLangGraph ではなく、従来のシンプルなワークフロー用の State。
    /api/analyze-simple から利用される。
    （/api/plan-keywords は現在は直接エージェントを呼び出しており、この State は使用しない）
    """

    # 入力
    seed_keyword: str
    site_profile: Optional[dict] = None

    # KeywordPlanner の出力
    keyword_plan: Optional[KeywordPlan] = None
    current_keyword: Optional[KeywordItem] = None

    # SERP エージェントの出力（キーワードごとの検索結果）
    serp_results: Dict[str, List[SerpResult]] = Field(default_factory=dict)

    # Parser エージェントの出力（キーワードごとのサイト構造）
    site_structures: Dict[str, List[SiteStructure]] = Field(default_factory=dict)

    # ★ Analyzer の結果
    analysis: Dict[str, KeywordStructureAnalysis] = Field(default_factory=dict)
