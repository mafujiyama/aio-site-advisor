# services/crawler.py

import requests


def fetch_html(url: str, timeout: float = 10.0) -> str:
    """
    単純な GET だけのクロール。
    テスト用なので、並列もリトライも入れていない。
    """
    headers = {
        "User-Agent": "aio-site-advisor/0.1 (+dev)",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text
