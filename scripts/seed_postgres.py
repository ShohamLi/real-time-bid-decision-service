import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.campaign_store import Campaign, SAMPLE_CAMPAIGNS  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main() -> None:
    with SessionLocal() as session:
        for campaign_data in SAMPLE_CAMPAIGNS:
            campaign = Campaign(**campaign_data)
            session.merge(campaign)
            print(f"Seeded {campaign.campaign_id}")

        session.commit()


if __name__ == "__main__":
    main()
