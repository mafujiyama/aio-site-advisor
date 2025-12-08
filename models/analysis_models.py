# models/analysis_models.py

from typing import List
from pydantic import BaseModel


class PageStructureMetrics(BaseModel):
    url: str
    domain: str
    title_length: int
    meta_description_length: int
    h1_count: int
    h2_count: int
    h3_count: int
    word_count: int
    keyword_in_title: bool
    keyword_in_h1: bool
    keyword_term_freq: int


class KeywordStructureAnalysis(BaseModel):
    keyword: str
    pages: List[PageStructureMetrics]
