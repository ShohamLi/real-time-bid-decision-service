import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.campaign_store import (
    Campaign,
    MemoryCampaignStore,
    PostgresCampaignStore,
    SAMPLE_CAMPAIGNS,
)
from app.models import BidRequest


def make_request(
    country: str = "IL",
    device: str = "mobile",
    placement: str = "mobile_feed",
) -> BidRequest:
    return BidRequest(
        impression_id="imp_campaign_test",
        user_id="user_sports_1",
        placement=placement,
        country=country,
        device=device,
        floor_price=1.2,
        context="sports shoes sale",
    )


def test_memory_store_returns_eligible_campaign():
    store = MemoryCampaignStore()

    campaign = store.get_eligible_campaign(make_request(), "sports", 2.45)

    assert campaign is not None
    assert campaign["campaign_id"] == "campaign_sports_il_mobile"
    assert campaign["creative_id"] == "creative_sports_001"


def test_inactive_campaign_is_ignored():
    inactive = next(
        campaign for campaign in SAMPLE_CAMPAIGNS if campaign["status"] == "inactive"
    )
    store = MemoryCampaignStore([inactive])

    assert store.get_eligible_campaign(make_request(), "sports", 2.0) is None


def test_exhausted_campaign_is_ignored():
    exhausted = next(
        campaign
        for campaign in SAMPLE_CAMPAIGNS
        if campaign["spent_today"] == campaign["daily_budget"]
    )
    store = MemoryCampaignStore([exhausted])

    assert store.get_eligible_campaign(make_request(), "sports", 2.0) is None


def test_memory_store_prevents_spending_above_daily_budget():
    campaign = SAMPLE_CAMPAIGNS[0].copy()
    campaign["daily_budget"] = 10.0
    campaign["spent_today"] = 9.0
    store = MemoryCampaignStore([campaign])

    assert store.record_spend(campaign["campaign_id"], 2.0) is False
    assert campaign["spent_today"] == 9.0


@pytest.mark.parametrize(
    ("country", "device", "placement"),
    [
        ("US", "mobile", "mobile_feed"),
        ("IL", "desktop", "mobile_feed"),
        ("IL", "mobile", "video_pre_roll"),
    ],
)
def test_wrong_targeting_is_ignored(country, device, placement):
    store = MemoryCampaignStore()

    campaign = store.get_eligible_campaign(
        make_request(country=country, device=device, placement=placement),
        "sports",
        2.0,
    )

    assert campaign is None


class FakeScalarResult:
    def __init__(self, campaign):
        self.campaign = campaign

    def first(self):
        return self.campaign


class FakeResult:
    def __init__(self, campaign):
        self.campaign = campaign

    def scalars(self):
        return FakeScalarResult(self.campaign)


class FakeSession:
    def __init__(self, campaign=None, error=None):
        self.campaign = campaign
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        if self.error:
            raise self.error
        return FakeResult(self.campaign)


def test_postgres_store_returns_campaign_without_real_database():
    campaign = Campaign(**SAMPLE_CAMPAIGNS[0])
    store = PostgresCampaignStore(session_factory=lambda: FakeSession(campaign))

    result = store.get_eligible_campaign(make_request(), "sports", 2.0)

    assert result is not None
    assert result["campaign_id"] == "campaign_sports_il_mobile"


def test_postgres_store_returns_none_when_query_fails():
    store = PostgresCampaignStore(
        session_factory=lambda: FakeSession(error=SQLAlchemyError("unavailable"))
    )

    result = store.get_eligible_campaign(make_request(), "sports", 2.0)

    assert result is None
