# Real-Time Bid Decision Service

A small HTTP service that receives impression events and returns a real-time bid decision.

The service simulates a simplified AdTech bidding flow: it validates an incoming impression request, retrieves user features from an in-memory feature store, enriches the request context with a local rule-based classifier, assigns the user to an A/B test group, calculates a score, and returns either `BID` or `NO_BID`.

## Tech Stack

- Python 3.11
- FastAPI
- Pydantic
- Redis
- pytest
- Docker

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/bid` | Creates a bid decision |
| GET | `/metrics` | Runtime metrics |

## Project Structure

```text
app/
  main.py              # FastAPI app, endpoints, runtime metrics
  models.py            # Pydantic request and response models
  config.py            # Configurable business parameters
  feature_store.py     # Memory and Redis feature-store backends
  scoring.py           # Scoring, A/B testing, bid decision logic
  ai_classifier.py     # Local context classification fallback

tests/
  test_api.py
  test_feature_store.py
  test_scoring.py

scripts/
  load_test.py
  seed_redis.py

Dockerfile
docker-compose.yml
requirements.txt
README.md
```

## Redis Feature Store

The service uses the in-memory feature store by default, so it runs without
Redis or additional configuration:

```bash
FEATURE_STORE_TYPE=memory
```

Redis mode uses a real online feature store. User features are stored as JSON
strings under keys such as `user_features:user_sports_1`.

```bash
FEATURE_STORE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

Start the application and Redis together:

```bash
docker compose up --build
```

Seed the existing sample users:

```bash
docker compose exec app python scripts/seed_redis.py
```

Test the required assignment endpoints:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/metrics
curl -X POST "http://127.0.0.1:8000/bid" \
  -H "Content-Type: application/json" \
  -d '{
    "impression_id": "imp_redis_1",
    "user_id": "user_sports_1",
    "placement": "mobile_feed",
    "country": "IL",
    "device": "mobile",
    "floor_price": 1.2,
    "context": "sports shoes sale"
  }'
```

If Redis is unavailable, times out, contains invalid JSON, or does not contain
the requested user, the service returns `DEFAULT_USER_FEATURES` with
`is_default=True`. Bid requests continue normally instead of crashing.
