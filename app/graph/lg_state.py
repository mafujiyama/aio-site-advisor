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

    TypedDict を使っているので、各キーは
    「存在するかもしれないし、しないかもしれない」状態（total=False）。
    ノード側では .get() などで安全に扱う前提。
    """

    # 入力
    seed_keyword: str
    site_profile: Optional[dict]

    # KeywordPlanner の出力
    keyword_plan: KeywordPlan

    # SERP エージェントの出力（キーワード → 検索結果リスト）
    serp_results: Dict[str, List[SerpResult]]

    # Parser エージェントの出力（キーワード → サイト構造リスト）
    site_structures: Dict[str, List[SiteStructure]]

    # Analyzer ノードの出力（キーワード → 分析結果）
    analysis: Dict[str, KeywordStructureAnalysis]

    # 進捗・ログ
    current_node: Optional[str]
    progress_messages: List[str]
