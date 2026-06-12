import threading
import time

from fastapi import FastAPI

from app.bid_decision_log import log_bid_decision
from app.campaign_store import get_campaign_store
from app.config import get_settings
from app.feature_store import get_user_features
from app.models import BidRequest, BidResponse
from app.scoring import make_bid_decision_result


app = FastAPI(
    title="Real-Time Bid Decision Service",
    version="0.1.0",
    description="A simplified real-time bidding decision service for impression events.",
)


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_requests = 0
        self.bid_count = 0
        self.no_bid_count = 0
        self.total_latency_ms = 0.0

    def record(self, decision: str, latency_ms: float) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms

            if decision == "BID":
                self.bid_count += 1
            else:
                self.no_bid_count += 1

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            average_latency_ms = (
                self.total_latency_ms / self.total_requests
                if self.total_requests > 0
                else 0.0
            )

            return {
                "total_requests": self.total_requests,
                "bid_count": self.bid_count,
                "no_bid_count": self.no_bid_count,
                "average_latency_ms": round(average_latency_ms, 2),
            }


metrics = RuntimeMetrics()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def get_metrics() -> dict[str, float | int]:
    return metrics.snapshot()


@app.post("/bid", response_model=BidResponse)
def create_bid_decision(request: BidRequest) -> BidResponse:
    start_time = time.perf_counter()

    settings = get_settings()
    features = get_user_features(request.user_id)
    result = make_bid_decision_result(
        request=request,
        features=features,
        settings=settings,
        campaign_store=get_campaign_store(),
    )
    response = result.response

    latency_ms = (time.perf_counter() - start_time) * 1000
    metrics.record(decision=response.decision, latency_ms=latency_ms)

    try:
        log_bid_decision(
            request=request,
            response=response,
            category=result.category,
            campaign_id=result.campaign_id,
        )
    except Exception:
        pass

    return response
