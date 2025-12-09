# services/html_parser.py

from __future__ import annotations

import re
from typing import List
import logging

import requests
from bs4 import BeautifulSoup

from models.site_models import SiteStructure, HeadingNode

logger = logging.getLogger(__name__)


def _build_heading_tree(soup: BeautifulSoup) -> List[HeadingNode]:
    """h1〜h6 を元に簡易的な階層ツリーを構築する。"""
    nodes: List[HeadingNode] = []
    stack: List[HeadingNode] = []

    for tag in soup.find_all(re.compile(r"h[1-6]")):
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        node = HeadingNode(level=level, text=text, children=[])

        # スタックを使って階層を構築
        while stack and stack[-1].level >= level:
            stack.pop()

        if not stack:
            nodes.append(node)
        else:
            stack[-1].children.append(node)

        stack.append(node)

    return nodes


def _extract_main_text(soup: BeautifulSoup) -> str:
    # 非表示要素や script / style を除外
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _tokenize(text: str) -> List[str]:
    # ひとまずスペース区切り＋記号除去の簡易版
    # （必要であれば後でJanomeなどを利用して日本語形態素解析に変更）
    text = re.sub(r"[^\wぁ-んァ-ン一-龥]+", " ", text)
    tokens = [t for t in text.split() if t]
    return tokens


def fetch_and_parse(url: str) -> SiteStructure:
    """URLからHTMLを取得し、構造化情報に変換する。"""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else url
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content") if meta_desc_tag else None

    h1_list = [h.get_text(strip=True) for h in soup.find_all("h1")]
    headings = [h.get_text(strip=True) for h in soup.find_all(re.compile(r"h[1-6]"))]
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
        headings=headings,
        heading_tree=heading_tree,
        main_text=main_text,
        word_count=len(tokens),
        term_freq=term_freq,
    )
