# services/llm_client.py
import os
from openai import OpenAI

_client: OpenAI | None = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY が設定されていません")
        _client = OpenAI(api_key=api_key)
    return _client
