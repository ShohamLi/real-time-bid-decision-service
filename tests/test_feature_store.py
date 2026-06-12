from app.feature_store import get_user_features


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
