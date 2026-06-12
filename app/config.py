from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bid_threshold: float = 0.65
    bid_multiplier: float = 1.4
    group_b_threshold_delta: float = 0.03
    group_b_bid_multiplier: float = 1.08
    max_ctr: float = 0.12
    enable_ai_enrichment: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()