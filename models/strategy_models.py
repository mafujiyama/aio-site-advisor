# models/strategy_models.py

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class KeywordStrategyItem(BaseModel):
    """
    キーワード単位の施策・方針。
    """
    keyword: str
    intent: Optional[str] = None
    priority: Optional[int] = None

    # このキーワードで狙うべきコンテンツの型
    # 例: "カテゴリページ", "製品一覧", "製品詳細", "コラム", "FAQ" など
    recommended_content_type: Optional[str] = None

    # 具体的な施策リスト
    recommended_actions: List[str] = []

    # 備考・メモ
    notes: Optional[str] = None


class StrategySummary(BaseModel):
    """
    全体のSEO/AIO戦略サマリ。
    """
    seed_keyword: str

    # 全体方針の概要テキスト
    overview: str

    # サイト全体に共通する推奨アクション
    global_recommendations: List[str] = []

    # キーワード別の戦略
    keyword_strategies: List[KeywordStrategyItem] = []
