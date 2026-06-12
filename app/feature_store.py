from typing import Any


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


def get_user_features(user_id: str) -> dict[str, Any]:
    """
    Simulates a real-time feature store lookup.

    If the user is unknown, default features are returned so the service
    can still make a safe decision instead of failing.
    """
    if user_id in USER_FEATURES:
        features = USER_FEATURES[user_id].copy()
        features["is_default"] = False
        return features

    features = DEFAULT_USER_FEATURES.copy()
    features["is_default"] = True
    return features