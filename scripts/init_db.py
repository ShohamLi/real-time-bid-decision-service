import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.bid_decision_log import BidDecision  # noqa: E402, F401
from app.campaign_store import Campaign  # noqa: E402, F401
from app.database import Base, engine  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Campaigns and bid_decisions tables created successfully")


if __name__ == "__main__":
    main()
