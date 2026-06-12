import json
import sys
from pathlib import Path

from redis import Redis


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.feature_store import USER_FEATURES  # noqa: E402


def main() -> None:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)

    for user_id, features in USER_FEATURES.items():
        key = f"user_features:{user_id}"
        client.set(key, json.dumps(features))
        print(f"Seeded {user_id} at {key}")


if __name__ == "__main__":
    main()
