# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()

