import json

from redis.exceptions import ConnectionError

from app.feature_store import (
    MemoryFeatureStore,
    RedisFeatureStore,
    get_user_features,
)


class FakeRedisClient:
    def __init__(self, values=None, error=None):
        self.values = values or {}
        self.error = error
        self.requested_keys = []

    def get(self, key):
        self.requested_keys.append(key)
        if self.error:
            raise self.error
        return self.values.get(key)


def test_known_user_features_are_returned():
    features = get_user_features("user_sports_1")

    assert features["segment"] == "sports"
    assert features["user_ctr"] == 0.09
    assert features["user_value"] == 0.85
    assert features["is_default"] is False


def test_unknown_user_gets_default_features():
    features = get_user_features("missing_user_123")

    assert features["segment"] == "unknown"
    assert features["user_ctr"] == 0.03
    assert features["is_default"] is True


def test_memory_feature_store_returns_known_user():
    store = MemoryFeatureStore()

    features = store.get_user_features("user_sports_1")

    assert features["segment"] == "sports"
    assert features["is_default"] is False


def test_redis_feature_store_returns_known_user():
    client = FakeRedisClient(
        {
            "user_features:user_sports_1": json.dumps(
                {
                    "user_ctr": 0.09,
                    "user_value": 0.85,
                    "segment": "sports",
                    "campaign_budget": 1200,
                }
            )
        }
    )
    store = RedisFeatureStore("redis://unused", client=client)

    features = store.get_user_features("user_sports_1")

    assert client.requested_keys == ["user_features:user_sports_1"]
    assert features["segment"] == "sports"
    assert features["is_default"] is False


def test_redis_feature_store_returns_defaults_for_missing_user():
    store = RedisFeatureStore("redis://unused", client=FakeRedisClient())

    features = store.get_user_features("missing_user")

    assert features["segment"] == "unknown"
    assert features["is_default"] is True


def test_redis_feature_store_returns_defaults_for_bad_json():
    client = FakeRedisClient({"user_features:user_sports_1": "not-json"})
    store = RedisFeatureStore("redis://unused", client=client)

    features = store.get_user_features("user_sports_1")

    assert features["segment"] == "unknown"
    assert features["is_default"] is True


def test_redis_feature_store_returns_defaults_when_unavailable():
    client = FakeRedisClient(error=ConnectionError("Redis unavailable"))
    store = RedisFeatureStore("redis://unused", client=client)

    features = store.get_user_features("user_sports_1")

    assert features["segment"] == "unknown"
    assert features["is_default"] is True
