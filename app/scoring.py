import hashlib
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from app.ai_classifier import classify_context
from app.campaign_store import get_campaign_store
from app.config import Settings
from app.models import BidRequest, BidResponse


if TYPE_CHECKING:
    from app.campaign_store import CampaignStore


CREATIVES_BY_CATEGORY: dict[str, str] = {
    "sports": "creative_sports_001",
    "finance": "creative_finance_001",
    "fashion": "creative_fashion_001",
    "gaming": "creative_gaming_001",
    "travel": "creative_travel_001",
    "unknown": "creative_generic_001",
}


@dataclass(frozen=True)
class BidDecisionResult:
    response: BidResponse
    category: str
    campaign_id: str | None


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def assign_experiment_group(user_id: str) -> str:
    """
    Deterministically assigns a user to A or B.

    Python's built-in hash is intentionally not used because it can change
    between processes. SHA-256 keeps the assignment stable.
    """
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "A" if bucket < 50 else "B"


def calculate_context_score(segment: str, category: str) -> float:
    if category == "unknown":
        return 0.35

    if segment == category:
        return 1.0

    if segment == "unknown":
        return 0.55

    return 0.65


def calculate_score(features: dict[str, Any], category: str, settings: Settings) -> float:
    """
    Score formula:

    ctr_signal    = normalized user CTR between 0 and 1
    user_value    = historical user value between 0 and 1
    context_score = relevance between user segment and page context

    Final score:
    45% CTR signal + 35% user value + 20% context relevance
    """
    user_ctr = float(features.get("user_ctr", 0.0))
    user_value = clamp(float(features.get("user_value", 0.0)))
    segment = str(features.get("segment", "unknown"))

    ctr_signal = clamp(user_ctr / settings.max_ctr)
    context_score = calculate_context_score(segment=segment, category=category)

    score = ctr_signal * 0.45 + user_value * 0.35 + context_score * 0.20
    return round(clamp(score), 4)


def get_threshold_for_group(group: str, settings: Settings) -> float:
    if group == "B":
        return settings.bid_threshold + settings.group_b_threshold_delta

    return settings.bid_threshold


def calculate_bid_price(score: float, features: dict[str, Any], group: str, settings: Settings) -> float:
    user_value = clamp(float(features.get("user_value", 0.0)))

    multiplier = settings.bid_multiplier
    if group == "B":
        multiplier *= settings.group_b_bid_multiplier

    bid_price = 0.3 + score * user_value * multiplier * 2.0
    return round(bid_price, 2)


def select_creative(category: str) -> str:
    return CREATIVES_BY_CATEGORY.get(category, CREATIVES_BY_CATEGORY["unknown"])


def make_bid_decision(
    request: BidRequest,
    features: dict[str, Any],
    settings: Settings,
    campaign_store: "CampaignStore | None" = None,
) -> BidResponse:
    return make_bid_decision_result(
        request=request,
        features=features,
        settings=settings,
        campaign_store=campaign_store,
    ).response


def make_bid_decision_result(
    request: BidRequest,
    features: dict[str, Any],
    settings: Settings,
    campaign_store: "CampaignStore | None" = None,
) -> BidDecisionResult:
    group = assign_experiment_group(request.user_id)

    category = (
        classify_context(request.context)
        if settings.enable_ai_enrichment
        else "unknown"
    )

    score = calculate_score(features=features, category=category, settings=settings)
    threshold = get_threshold_for_group(group=group, settings=settings)
    calculated_bid_price = calculate_bid_price(
        score=score,
        features=features,
        group=group,
        settings=settings,
    )

    should_bid = score >= threshold and calculated_bid_price >= request.floor_price

    if should_bid:
        store = campaign_store or get_campaign_store()
        campaign = store.get_eligible_campaign(
            request=request,
            category=category,
            bid_price=calculated_bid_price,
        )
        if campaign is None:
            return BidDecisionResult(
                response=BidResponse(
                    impression_id=request.impression_id,
                    decision="NO_BID",
                    bid_price=None,
                    creative_id=None,
                    experiment_group=group,
                    score=score,
                    reason="No eligible campaign found",
                ),
                category=category,
                campaign_id=None,
            )

        final_bid_price = min(calculated_bid_price, float(campaign["max_bid"]))
        reason = "High predicted value and bid price is above floor price"
        if features.get("is_default"):
            reason += "; default user features were used"

        return BidDecisionResult(
            response=BidResponse(
                impression_id=request.impression_id,
                decision="BID",
                bid_price=final_bid_price,
                creative_id=str(campaign["creative_id"]),
                experiment_group=group,
                score=score,
                reason=reason,
            ),
            category=category,
            campaign_id=str(campaign["campaign_id"]),
        )

    if score < threshold:
        reason = "Score is below experiment threshold"
    else:
        reason = "Calculated bid price is below floor price"

    if features.get("is_default"):
        reason += "; default user features were used"

    return BidDecisionResult(
        response=BidResponse(
            impression_id=request.impression_id,
            decision="NO_BID",
            bid_price=None,
            creative_id=None,
            experiment_group=group,
            score=score,
            reason=reason,
        ),
        category=category,
        campaign_id=None,
    )
