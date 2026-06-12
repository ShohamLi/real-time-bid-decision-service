import json
from functools import lru_cache
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.config import get_settings


DEFAULT_USER_FEATURES: dict[str, Any] = {
    "user_ctr": 0.03,
    "user_value": 0.45,
    "segment": "unknown",
    "campaign_budget": 500,
}


USER_FEATURES: dict[str, dict[str, Any]] = {
    "user_sports_1": {
        "user_ctr": 0.09,
        "user_value": 0.85,
        "segment": "sports",
        "campaign_budget": 1200,
    },
    "user_finance_1": {
        "user_ctr": 0.06,
        "user_value": 0.75,
        "segment": "finance",
        "campaign_budget": 1800,
    },
    "user_fashion_1": {
        "user_ctr": 0.07,
        "user_value": 0.8,
        "segment": "fashion",
        "campaign_budget": 950,
    },
    "user_low_value_1": {
        "user_ctr": 0.01,
        "user_value": 0.25,
        "segment": "unknown",
        "campaign_budget": 300,
    },
}


class MemoryFeatureStore:
    def __init__(self, features: dict[str, dict[str, Any]] | None = None) -> None:
        self.features = USER_FEATURES if features is None else features

    def get_user_features(self, user_id: str) -> dict[str, Any]:
        features = self.features.get(user_id)
        if features is None:
            return _default_features()

        return {**features, "is_default": False}


class RedisFeatureStore:
    def __init__(self, redis_url: str, client: Any | None = None) -> None:
        self.redis_url = redis_url
        self.client = client

    def get_user_features(self, user_id: str) -> dict[str, Any]:
        try:
            raw = self._get_client().get(_feature_key(user_id))
            if raw is None:
                return _default_features()

            features = json.loads(raw)
            if not isinstance(features, dict):
                return _default_features()

            return {**features, "is_default": False}
        except (RedisError, TimeoutError, ValueError, TypeError):
            return _default_features()

    def _get_client(self):
        if self.client is None:
            self.client = Redis.from_url(self.redis_url, decode_responses=True)
        return self.client


@lru_cache
def _get_feature_store(
    feature_store_type: str,
    redis_url: str,
) -> MemoryFeatureStore | RedisFeatureStore:
    if feature_store_type.lower() == "redis":
        return RedisFeatureStore(redis_url)

    return MemoryFeatureStore()


def get_user_features(user_id: str) -> dict[str, Any]:
    settings = get_settings()
    store = _get_feature_store(settings.feature_store_type, settings.redis_url)
    return store.get_user_features(user_id)


def _default_features() -> dict[str, Any]:
    return {**DEFAULT_USER_FEATURES, "is_default": True}


def _feature_key(user_id: str) -> str:
    return f"user_features:{user_id}"
