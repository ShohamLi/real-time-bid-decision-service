from fastapi import FastAPI

from app.models import BidRequest, BidResponse

app = FastAPI(
    title="Real-Time Bid Decision Service",
    version="1.0.0",
    description="A simplified real-time bid decision service for an AdTech take-home assignment.",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/bid", response_model=BidResponse)
def create_bid_decision(request: BidRequest):
    return BidResponse(
        impression_id=request.impression_id,
        decision="BID",
        bid_price=round(request.floor_price * 1.2, 2),
        creative_id="creative_default_001",
        experiment_group="A",
        score=0.75,
        reason="Temporary mock response. Real scoring logic will be added later.",
    )