# models/site_models.py

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HeadingNode(BaseModel):
    """
    見出し階層の1ノード（h1〜h6）。
    - level: 見出しレベル (1〜6)
    - text: 見出しのテキスト
    - children: 子ノード（入れ子の見出し）
    """
    level: int
    text: str
    children: List["HeadingNode"] = Field(default_factory=list)


class SiteStructure(BaseModel):
    """
    1ページ分の構造情報。
    解析結果を Analyzer や 将来の LLM に渡すための中間モデル。
    """

    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None

    # h1 はシンプルにテキストだけのリストを保持
    h1_list: List[str] = Field(default_factory=list)

    # すべての見出しを HeadingNode の「フラットなリスト」として保持
    # （Analyzer ではここから h2_count / h3_count などを集計）
    headings: List[HeadingNode] = Field(default_factory=list)

    # 見出し階層ツリー（ルートノードのリスト）
    heading_tree: List[HeadingNode] = Field(default_factory=list)

    # 本文テキストと、その統計値
    main_text: str = ""
    word_count: int = 0
    term_freq: Dict[str, int] = Field(default_factory=dict)
