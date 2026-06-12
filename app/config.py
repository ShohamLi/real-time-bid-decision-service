from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bid_threshold: float = 0.65
    bid_multiplier: float = 1.4
    group_b_threshold_delta: float = 0.03
    group_b_bid_multiplier: float = 1.08
    max_ctr: float = 0.12
    enable_ai_enrichment: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 1.0
    feature_store_type: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    campaign_store_type: str = "memory"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/bid_service"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
