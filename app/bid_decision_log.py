from datetime import datetime
from typing import Protocol

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, SessionLocal
from app.models import BidRequest, BidResponse


class BidDecision(Base):
    __tablename__ = "bid_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    impression_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    placement: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    device: Mapped[str] = mapped_column(String(20), nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    experiment_group: Mapped[str] = mapped_column(String(1), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    bid_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    creative_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BidDecisionLogger(Protocol):
    def log(
        self,
        request: BidRequest,
        response: BidResponse,
        category: str,
        campaign_id: str | None,
    ) -> bool: ...


class PostgresBidDecisionLogger:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    def log(
        self,
        request: BidRequest,
        response: BidResponse,
        category: str,
        campaign_id: str | None,
    ) -> bool:
        record = BidDecision(
            impression_id=request.impression_id,
            user_id=request.user_id,
            placement=request.placement,
            country=request.country,
            device=request.device,
            floor_price=request.floor_price,
            context=request.context,
            category=category,
            experiment_group=response.experiment_group,
            score=response.score,
            decision=response.decision,
            bid_price=response.bid_price,
            creative_id=response.creative_id,
            campaign_id=campaign_id,
            reason=response.reason,
        )

        try:
            with self.session_factory() as session:
                session.add(record)
                session.commit()
            return True
        except SQLAlchemyError:
            return False


_logger = PostgresBidDecisionLogger()


def log_bid_decision(
    request: BidRequest,
    response: BidResponse,
    category: str,
    campaign_id: str | None,
) -> bool:
    try:
        return _logger.log(request, response, category, campaign_id)
    except Exception:
        return False
