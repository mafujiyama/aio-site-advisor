# models/keyword_models.py

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Literal, Optional


# -----------------------------------------
# Intent（検索意図）
# -----------------------------------------
IntentType = Literal[
    "KNOW",         # 情報収集: What/How/Why
    "COMPARE",      # 比較・検討
    "BUY",          # 購買意図
    "NAVIGATIONAL"  # 指名・特定サイトへ
]


# -----------------------------------------
# LLMが生成する“生の案”（アイデア）
# → category や priority を LLMがつけたり、人が後処理する前提
# -----------------------------------------
class KeywordIdea(BaseModel):
    """LLM が生成するキーワード案（生データ）を表すモデル。

    Attributes:
        keyword (str): 派生キーワード案。
        intent (IntentType | None): 推定検索意図（省略可）。
        category (str | None): カテゴリ分類（任意）。
        reason (str | None): このキーワードを提案した理由（任意）。
    """

    keyword: str = Field(..., description="派生キーワード案")
    intent: Optional[IntentType] = Field(None, description="検索意図（任意）")
    category: Optional[str] = Field(None, description="カテゴリ分類")
    reason: Optional[str] = Field(None, description="選定理由")


# -----------------------------------------
# 整形済みのキーワード項目
# → LLMの KeywordIdea を KeywordItem に変換して使用
# -----------------------------------------
class KeywordItem(BaseModel):
    """アプリ内部で使う整形済みキーワード項目。

    Attributes:
        keyword (str): キーワード文字列。
        intent (IntentType): 検索意図（必須）。
        category (str | None): 任意のカテゴリ分類。
        priority (int): 重要度（1〜5）。
        reason (str | None): キーワードの解説。
    """

    keyword: str
    intent: IntentType
    category: Optional[str] = None
    priority: int = Field(3, ge=1, le=5)
    reason: Optional[str] = None


# -----------------------------------------
# キーワードプラン（内部で使うデータ構造）
# -----------------------------------------
class KeywordPlan(BaseModel):
    """キーワードプラン（種キーワードと派生キーワード一覧）を管理するモデル。

    Attributes:
        seed_keyword (str): 起点キーワード。
        items (List[KeywordItem]): 整形済みキーワード項目。
    """

    seed_keyword: str
    items: List[KeywordItem] = Field(default_factory=list)

    # ------------------------------
    # priorityの高い順に並び替え
    # ------------------------------
    def top_keywords(self, limit: int = 10) -> List[KeywordItem]:
        """priority が高い順に上位キーワードを取得する。

        Args:
            limit (int): 返却件数。
        Returns:
            List[KeywordItem]: 上位 priority のキーワードのリスト。
        """
        return sorted(self.items, key=lambda k: k.priority, reverse=True)[:limit]

    # ------------------------------
    # intent 別のグループ化（レポート用）
    # ------------------------------
    def group_by_intent(self) -> dict[str, List[KeywordItem]]:
        """intent（検索意図）別にキーワードをグループ化する。

        Returns:
            dict[str, List[KeywordItem]]:
                intent をキーとし、その intent に対応するキーワードリスト。
        """
        groups = {"KNOW": [], "COMPARE": [], "BUY": [], "NAVIGATIONAL": []}
        for item in self.items:
            groups[item.intent].append(item)
        return groups

    # ------------------------------
    # category 別のグループ化（レポート用）
    # ------------------------------
    def group_by_category(self) -> dict[str, List[KeywordItem]]:
        """category 別にキーワードをグループ化する。

        Returns:
            dict[str, List[KeywordItem]]:
                category をキーとしたキーワード辞書。
        """
        result: dict[str, List[KeywordItem]] = {}
        for item in self.items:
            if not item.category:
                continue
            result.setdefault(item.category, []).append(item)
        return result

    # ------------------------------
    # KeywordIdea → KeywordItem 変換
    # ------------------------------
    @staticmethod
    def from_ideas(seed_keyword: str, ideas: List[KeywordIdea]) -> "KeywordPlan":
        """KeywordIdea（LLMの生データ）から KeywordPlan を生成する。

        Notes:
            - priority は初期値 3 を採用。
            - intent が None の場合は KNOW で補完。
            - category / reason はそのまま移行。

        Returns:
            KeywordPlan: 変換後の整形済みキーワードプラン。
        """
        items = []
        for idea in ideas:
            items.append(
                KeywordItem(
                    keyword=idea.keyword,
                    intent=idea.intent or "KNOW",
                    category=idea.category,
                    reason=idea.reason,
                    priority=3,
                )
            )
        return KeywordPlan(seed_keyword=seed_keyword, items=items)
