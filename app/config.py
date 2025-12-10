# app/config.py

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    アプリ全体で使う設定クラス。
    .env から環境変数を読み込み、属性として参照できるようにする。
    """

    # ---------- OpenAI ----------
    # OPENAI_API_KEY=sk-xxxx... を .env に書く想定
    openai_api_key: str | None = None

    # keyword_planner から参照されるフィールド
    # モデル名を変えたい場合は .env に
    # OPENAI_MODEL=gpt-4.1 などと書けば上書きされる
    openai_model: str = "gpt-4.1-mini"

    # ---------- Google Custom Search ----------
    # GOOGLE_SEARCH_API_KEY=...
    # GOOGLE_SEARCH_CX=... を .env に書く想定
    google_search_api_key: str | None = None
    google_search_cx: str | None = None

    # ---------- Pydantic Settings 設定 ----------
    model_config = SettingsConfigDict(
        env_file=".env",            # .env を読む
        env_file_encoding="utf-8",
        extra="ignore",             # 定義外の環境変数があっても無視（エラーにしない）
    )


@lru_cache
def get_settings() -> Settings:
    """Settings をシングルトン的に使うためのヘルパ。"""
    return Settings()


# 他のモジュールからは `from app.config import settings` で利用
settings = get_settings()
