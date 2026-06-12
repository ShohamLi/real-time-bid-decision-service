from sqlalchemy.exc import OperationalError

from app.bid_decision_log import PostgresBidDecisionLogger
from app.models import BidRequest, BidResponse


def make_request() -> BidRequest:
    return BidRequest(
        impression_id="imp_log_test",
        user_id="user_sports_1",
        placement="mobile_feed",
        country="IL",
        device="mobile",
        floor_price=1.2,
        context="sports shoes sale",
    )


def make_response() -> BidResponse:
    return BidResponse(
        impression_id="imp_log_test",
        decision="BID",
        bid_price=2.45,
        creative_id="creative_sports_001",
        experiment_group="B",
        score=0.835,
        reason="High predicted value and bid price is above floor price",
    )


class FakeSession:
    def __init__(self, error=None) -> None:
        self.error = error
        self.record = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def add(self, record) -> None:
        self.record = record

    def commit(self) -> None:
        if self.error:
            raise self.error
        self.committed = True


def test_postgres_logger_stores_complete_decision_without_real_database():
    session = FakeSession()
    logger = PostgresBidDecisionLogger(session_factory=lambda: session)

    logged = logger.log(
        request=make_request(),
        response=make_response(),
        category="sports",
        campaign_id="campaign_sports_il_mobile",
    )

    assert logged is True
    assert session.committed is True
    assert session.record.impression_id == "imp_log_test"
    assert session.record.user_id == "user_sports_1"
    assert session.record.placement == "mobile_feed"
    assert session.record.country == "IL"
    assert session.record.device == "mobile"
    assert session.record.floor_price == 1.2
    assert session.record.context == "sports shoes sale"
    assert session.record.category == "sports"
    assert session.record.experiment_group == "B"
    assert session.record.score == 0.835
    assert session.record.decision == "BID"
    assert session.record.bid_price == 2.45
    assert session.record.creative_id == "creative_sports_001"
    assert session.record.campaign_id == "campaign_sports_il_mobile"
    assert session.record.reason == make_response().reason


def test_postgres_logger_returns_false_when_database_is_unavailable():
    error = OperationalError("statement", {}, Exception("database unavailable"))
    logger = PostgresBidDecisionLogger(
        session_factory=lambda: FakeSession(error=error)
    )

    assert logger.log(make_request(), make_response(), "sports", None) is False
