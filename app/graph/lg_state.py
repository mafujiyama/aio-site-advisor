# app/graph/lg_state.py

from typing import Dict, List, Optional
from typing_extensions import TypedDict

from models.keyword_models import KeywordPlan
from models.serp_models import SerpResult
from models.site_models import SiteStructure
from models.analysis_models import KeywordStructureAnalysis


class GraphState(TypedDict, total=False):
    """
    LangGraph 用の State 定義。
    実体は「ただの dict」だが、
    キーと値の型をわかりやすくするため TypedDict で型定義している。
    """

    # 入力
    seed_keyword: str
    site_profile: Optional[dict]

    # KeywordPlanner の出力
    keyword_plan: KeywordPlan

    # SERP エージェントの出力
    serp_results: Dict[str, List[SerpResult]]

    # Parser エージェントの出力（URL → 構造）
    site_structures: Dict[str, List[SiteStructure]]

    # Analyzer ノードの出力
    analysis: Dict[str, KeywordStructureAnalysis]

    # 進捗・ログ
    current_node: str
    progress_messages: List[str]
