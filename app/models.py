from typing import Literal

from pydantic import BaseModel, Field


DeviceType = Literal["mobile", "desktop", "tablet"]
PlacementType = Literal["mobile_feed", "desktop_banner", "video_pre_roll"]
DecisionType = Literal["BID", "NO_BID"]
ExperimentGroup = Literal["A", "B"]


class BidRequest(BaseModel):
    impression_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    placement: PlacementType
    country: str = Field(..., min_length=2, max_length=2)
    device: DeviceType
    floor_price: float = Field(..., ge=0)
    context: str | None = None


class BidResponse(BaseModel):
    impression_id: str
    decision: DecisionType
    bid_price: float | None
    creative_id: str | None
    experiment_group: ExperimentGroup
    score: float = Field(..., ge=0, le=1)
    reason: str