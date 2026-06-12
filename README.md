# Real-Time Bid Decision Service

A small HTTP service that receives impression events and returns a real-time bid decision.

The service simulates a simplified AdTech bidding flow: it validates an incoming impression request, retrieves user features from an in-memory feature store, enriches the request context with a local rule-based classifier, assigns the user to an A/B test group, calculates a score, and returns either `BID` or `NO_BID`.

## Tech Stack

- Python 3.11
- FastAPI
- Pydantic
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
  feature_store.py     # In-memory feature store simulation
  scoring.py           # Scoring, A/B testing, bid decision logic
  ai_classifier.py     # Local context classification fallback

tests/
  test_api.py
  test_feature_store.py
  test_scoring.py

scripts/
  load_test.py

Dockerfile
requirements.txt
README.md
