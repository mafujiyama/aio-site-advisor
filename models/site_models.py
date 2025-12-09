# models/site_models.py

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class HeadingNode(BaseModel):
    level: int            # 1〜6
    text: str
    children: List["HeadingNode"] = []


class SiteStructure(BaseModel):
    url: str
    title: str
    meta_description: Optional[str] = None
    h1_list: List[str] = []
    headings: List[str] = []  # 従来の平坦なリストは残す
    heading_tree: List[HeadingNode] = []   # ★ 階層ツリー
    main_text: str
    word_count: int
    # TF-IDF用の素データ（単純な term → tf）
    term_freq: dict[str, int] = {}
