# services/html_parser.py

from typing import List, Optional
from bs4 import BeautifulSoup   # pip install beautifulsoup4

from models.site_models import SiteStructure, Heading


def extract_main_text(soup: BeautifulSoup) -> str:
    """
    超ざっくり版の本文抽出：
    - script/style/nav/footer などは除外
    - 残りのテキストを連結
    """
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    texts: List[str] = []
    for elem in soup.find_all(text=True):
        t = elem.strip()
        if t:
            texts.append(t)
    return " ".join(texts)


def parse_html(url: str, html: str) -> SiteStructure:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else None

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description: Optional[str] = None
    if meta_desc_tag and meta_desc_tag.get("content"):
        meta_description = meta_desc_tag["content"].strip()

    # h1
    h1_list: List[str] = [h.get_text(strip=True) for h in soup.find_all("h1")]

    # h2/h3 他
    headings: List[Heading] = []
    for level in [2, 3]:
        for tag in soup.find_all(f"h{level}"):
            text = tag.get_text(strip=True)
            if text:
                headings.append(Heading(level=level, text=text))

    main_text = extract_main_text(soup)
    word_count = len(main_text.split()) if main_text else 0

    return SiteStructure(
        url=url,
        title=title,
        meta_description=meta_description,
        h1_list=h1_list,
        headings=headings,
        main_text=main_text,
        word_count=word_count,
    )
