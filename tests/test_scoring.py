from app.config import Settings
from app.feature_store import get_user_features
from app.models import BidRequest
from app.scoring import (
    assign_experiment_group,
    calculate_score,
    make_bid_decision,
)


def make_request(
    user_id: str = "user_sports_1",
    floor_price: float = 1.2,
    context: str = "sports shoes sale",
) -> BidRequest:
    return BidRequest(
        impression_id="imp_test",
        user_id=user_id,
        placement="mobile_feed",
        country="IL",
        device="mobile",
        floor_price=floor_price,
        context=context,
    )


def test_experiment_group_assignment_is_stable():
    first_group = assign_experiment_group("user_sports_1")
    second_group = assign_experiment_group("user_sports_1")

    assert first_group == second_group
    assert first_group in {"A", "B"}


def test_score_is_high_for_matching_sports_context():
    settings = Settings()
    features = get_user_features("user_sports_1")

    score = calculate_score(
        features=features,
        category="sports",
        settings=settings,
    )

    assert score >= settings.bid_threshold


def test_bid_when_score_is_high_and_bid_price_is_above_floor():
    settings = Settings()
    request = make_request(floor_price=1.2)
    features = get_user_features(request.user_id)

    response = make_bid_decision(
        request=request,
        features=features,
        settings=settings,
    )

    assert response.decision == "BID"
    assert response.bid_price is not None
    assert response.bid_price >= request.floor_price
    assert response.creative_id == "creative_sports_001"


def test_no_bid_when_floor_price_is_too_high():
    settings = Settings()
    request = make_request(floor_price=20.0)
    features = get_user_features(request.user_id)

    response = make_bid_decision(
        request=request,
        features=features,
        settings=settings,
    )

    assert response.decision == "NO_BID"
    assert response.bid_price is None
    assert response.creative_id is None
    assert "floor price" in response.reason


def test_unknown_user_can_still_get_decision():
    settings = Settings()
    request = make_request(
        user_id="new_user_123",
        floor_price=1.2,
        context="random article",
    )
    features = get_user_features(request.user_id)

    response = make_bid_decision(
        request=request,
        features=features,
        settings=settings,
    )

    assert response.decision in {"BID", "NO_BID"}
    assert "default user features were used" in response.reason
