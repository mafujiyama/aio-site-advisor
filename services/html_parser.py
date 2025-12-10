# services/html_parser.py

from __future__ import annotations

import re
from typing import List
import logging

import requests
from bs4 import BeautifulSoup

from models.site_models import SiteStructure, HeadingNode

logger = logging.getLogger(__name__)


def _build_heading_nodes(soup: BeautifulSoup) -> List[HeadingNode]:
    """
    h1〜h6 を HeadingNode のフラットなリストとして生成する。
    Analyzer はここから h2_count, h3_count を集計する。
    """
    nodes: List[HeadingNode] = []
    for tag in soup.find_all(re.compile(r"h[1-6]")):
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        nodes.append(HeadingNode(level=level, text=text, children=[]))
    return nodes


def _build_heading_tree(soup: BeautifulSoup) -> List[HeadingNode]:
    """
    h1〜h6 から簡易的な階層ツリーを構築する。
    - h1 < h2 < h3 ... のように、level を見て親子関係を決める。
    """
    root_nodes: List[HeadingNode] = []
    stack: List[HeadingNode] = []

    for tag in soup.find_all(re.compile(r"h[1-6]")):
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        node = HeadingNode(level=level, text=text, children=[])

        # 自分以下のレベルをすべて pop して親を探す
        while stack and stack[-1].level >= level:
            stack.pop()

        if not stack:
            # 親がいない → ルートノード
            root_nodes.append(node)
        else:
            # 直近の lower-level ノードの子としてぶら下げる
            stack[-1].children.append(node)

        stack.append(node)

    return root_nodes


def _extract_main_text(soup: BeautifulSoup) -> str:
    """script/style 等を除去して本文テキストを抽出する。"""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _tokenize(text: str) -> List[str]:
    """
    ひとまずスペース区切り＋記号除去の簡易版。
    （必要であれば後で Janome などに差し替え予定）
    """
    text = re.sub(r"[^\wぁ-んァ-ン一-龥]+", " ", text)
    tokens = [t for t in text.split() if t]
    return tokens


def parse_html(url: str, html: str) -> SiteStructure:
    """
    HTML文字列を解析して SiteStructure を生成する。
    ※ ここではネットワークアクセスは行わない（fetch_html で取得済み前提）
    """
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else url
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content") if meta_desc_tag else None

    # h1 はテキストだけ持つ
    h1_list = [h.get_text(strip=True) for h in soup.find_all("h1")]

    # HeadingNode のリストとツリーの両方を生成
    heading_nodes = _build_heading_nodes(soup)
    heading_tree = _build_heading_tree(soup)

    main_text = _extract_main_text(soup)
    tokens = _tokenize(main_text)
    term_freq = {}
    for t in tokens:
        term_freq[t] = term_freq.get(t, 0) + 1

    return SiteStructure(
        url=url,
        title=title,
        meta_description=meta_description,
        h1_list=h1_list,
        headings=heading_nodes,      # ★ ここが HeadingNode のリスト
        heading_tree=heading_tree,   # ★ 階層構造
        main_text=main_text,
        word_count=len(tokens),
        term_freq=term_freq,
    )


def fetch_and_parse(url: str) -> SiteStructure:
    """
    URL から直接 HTML を取得してパースする従来の関数。
    （もし他の場所でまだ使っていれば後方互換のために残す）

    新しい構成では：
      crawler.fetch_html() → parse_html(url, html)
    を基本パスとし、この関数はラッパとして扱う。
    """
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    html = resp.text

    return parse_html(url, html)
