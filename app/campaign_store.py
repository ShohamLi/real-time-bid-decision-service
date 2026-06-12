from functools import lru_cache
from typing import Any, Protocol

from sqlalchemy import Float, String, case, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.database import Base, SessionLocal
from app.models import BidRequest


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    target_country: Mapped[str] = mapped_column(String(2), nullable=False)
    target_device: Mapped[str] = mapped_column(String(20), nullable=False)
    target_placement: Mapped[str] = mapped_column(String(50), nullable=False)
    daily_budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent_today: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    max_bid: Mapped[float] = mapped_column(Float, nullable=False)
    creative_id: Mapped[str] = mapped_column(String(100), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status,
            "category": self.category,
            "target_country": self.target_country,
            "target_device": self.target_device,
            "target_placement": self.target_placement,
            "daily_budget": self.daily_budget,
            "spent_today": self.spent_today,
            "max_bid": self.max_bid,
            "creative_id": self.creative_id,
        }


SAMPLE_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_id": "campaign_sports_il_mobile",
        "status": "active",
        "category": "sports",
        "target_country": "IL",
        "target_device": "mobile",
        "target_placement": "mobile_feed",
        "daily_budget": 1000.0,
        "spent_today": 150.0,
        "max_bid": 3.0,
        "creative_id": "creative_sports_001",
    },
    {
        "campaign_id": "campaign_finance_us_desktop",
        "status": "active",
        "category": "finance",
        "target_country": "US",
        "target_device": "desktop",
        "target_placement": "desktop_banner",
        "daily_budget": 1500.0,
        "spent_today": 300.0,
        "max_bid": 2.5,
        "creative_id": "creative_finance_001",
    },
    {
        "campaign_id": "campaign_sports_inactive",
        "status": "inactive",
        "category": "sports",
        "target_country": "IL",
        "target_device": "mobile",
        "target_placement": "mobile_feed",
        "daily_budget": 1000.0,
        "spent_today": 0.0,
        "max_bid": 4.0,
        "creative_id": "creative_sports_inactive",
    },
    {
        "campaign_id": "campaign_sports_exhausted",
        "status": "active",
        "category": "sports",
        "target_country": "IL",
        "target_device": "mobile",
        "target_placement": "mobile_feed",
        "daily_budget": 500.0,
        "spent_today": 500.0,
        "max_bid": 4.0,
        "creative_id": "creative_sports_exhausted",
    },
]


class CampaignStore(Protocol):
    def get_eligible_campaign(
        self,
        request: BidRequest,
        category: str,
        bid_price: float | None = None,
    ) -> dict[str, Any] | None: ...


class MemoryCampaignStore:
    def __init__(self, campaigns: list[dict[str, Any]] | None = None) -> None:
        self.campaigns = SAMPLE_CAMPAIGNS if campaigns is None else campaigns

    def get_eligible_campaign(
        self,
        request: BidRequest,
        category: str,
        bid_price: float | None = None,
    ) -> dict[str, Any] | None:
        for campaign in self.campaigns:
            if _is_eligible(campaign, request, category, bid_price):
                return campaign.copy()

        return None


class PostgresCampaignStore:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    def get_eligible_campaign(
        self,
        request: BidRequest,
        category: str,
        bid_price: float | None = None,
    ) -> dict[str, Any] | None:
        try:
            with self.session_factory() as session:
                statement = select(Campaign).where(
                    Campaign.status == "active",
                    Campaign.target_country == request.country,
                    Campaign.target_device == request.device,
                    Campaign.target_placement == request.placement,
                    or_(Campaign.category == category, Campaign.category == "generic"),
                    Campaign.spent_today < Campaign.daily_budget,
                )

                if bid_price is not None:
                    statement = statement.where(Campaign.max_bid >= request.floor_price)

                statement = statement.order_by(
                    case((Campaign.category == category, 0), else_=1),
                    Campaign.campaign_id,
                )
                campaign = session.execute(statement).scalars().first()
                return campaign.to_dict() if campaign else None
        except SQLAlchemyError:
            return None


@lru_cache
def _get_campaign_store(campaign_store_type: str) -> CampaignStore:
    if campaign_store_type.lower() == "postgres":
        return PostgresCampaignStore()

    return MemoryCampaignStore()


def get_campaign_store() -> CampaignStore:
    return _get_campaign_store(get_settings().campaign_store_type)


def get_eligible_campaign(
    request: BidRequest,
    category: str,
    bid_price: float | None = None,
) -> dict[str, Any] | None:
    return get_campaign_store().get_eligible_campaign(request, category, bid_price)


def _is_eligible(
    campaign: dict[str, Any],
    request: BidRequest,
    category: str,
    bid_price: float | None,
) -> bool:
    if campaign["status"] != "active":
        return False
    if campaign["target_country"] != request.country:
        return False
    if campaign["target_device"] != request.device:
        return False
    if campaign["target_placement"] != request.placement:
        return False
    if campaign["category"] not in {category, "generic"}:
        return False
    if float(campaign["spent_today"]) >= float(campaign["daily_budget"]):
        return False
    if bid_price is not None and float(campaign["max_bid"]) < request.floor_price:
        return False

    return True
