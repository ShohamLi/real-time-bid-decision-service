# Real-Time Bid Decision Service

## Project overview

This repository contains a small FastAPI service that makes an explainable bid
decision for an advertising impression. It validates the request, looks up user
features, classifies page context, assigns a deterministic A/B group, scores the
opportunity, finds an eligible campaign, and returns either `BID` or `NO_BID`.

The default configuration runs locally with in-memory user features and
campaigns. Redis and PostgreSQL adapters are included for a more realistic
online setup, and Docker Compose starts all three services.

## Features

- `POST /bid` with Pydantic validation and a stable response schema
- `GET /health` and process-local `GET /metrics`
- Configurable, explainable scoring and bid-price calculation
- Deterministic 50/50 A/B assignment based on `user_id`
- Redis user-feature lookup with safe default features on failure or a miss
- PostgreSQL campaign eligibility with an in-memory alternative
- Campaign-provided creative selection and `max_bid` capping
- Best-effort campaign spend updates after a `BID`
- Best-effort PostgreSQL decision logging
- Optional OpenAI context classification with local rule-based fallback
- Unit and API tests plus a small concurrent load-test script

## Architecture

```mermaid
flowchart TD
    A["POST /bid"] --> B["Pydantic validation"]
    B --> C["Redis or memory user features"]
    C --> D["OpenAI or local context classification"]
    D --> E["Scoring and deterministic A/B assignment"]
    E --> F{"Score and candidate bid pass?"}
    F -->|Yes| G["PostgreSQL or memory campaign eligibility"]
    F -->|No| I["NO_BID"]
    G --> H{"Eligible campaign?"}
    H -->|Yes| J["BID with campaign creative and capped price"]
    H -->|No| I
    J --> K["Best-effort campaign spend update"]
    K --> L["Best-effort PostgreSQL decision logging"]
    I --> L
    L --> M["API response"]
```

Invalid requests stop at validation and FastAPI returns `422 Unprocessable
Entity`. PostgreSQL decision logging is attempted only for requests that reach a
bid decision.

## End-to-end `/bid` flow

1. FastAPI validates the body as `BidRequest`.
2. The configured feature store loads the user record. Missing or unavailable
   Redis data becomes a marked set of default features.
3. Context is classified locally, or by OpenAI when explicitly enabled. Any AI
   failure falls back to the local result.
4. The service deterministically assigns the user to experiment group A or B.
5. It calculates a score, group threshold, and candidate bid price.
6. If the score or floor-price check fails, the result is `NO_BID`.
7. Otherwise, the configured campaign store looks for an eligible campaign. No
   match, including a PostgreSQL query failure, produces `NO_BID`.
8. A matched campaign supplies the creative, and its `max_bid` caps the price.
9. For `BID`, the service attempts to add the final price to `spent_today`.
10. The service updates in-process metrics, attempts to log the completed
    decision to PostgreSQL, and returns the response.

## Technology choices

- **FastAPI and Pydantic** provide a small typed HTTP layer and automatic request
  validation.
- **Redis** is appropriate for low-latency user features that are read on the
  request path.
- **PostgreSQL and SQLAlchemy** store durable campaign configuration, budget
  state, and decision history.
- **OpenAI is optional** because a synchronous external dependency should not be
  required for the bidder to operate; local classification protects the request
  path.
- **The scoring formula is intentionally simple and explainable** so each bid can
  be understood without a trained model.

Kafka, Kubernetes, a trained ML model, and advanced budget pacing would be
reasonable production evolutions, but they are outside this assignment's scope.

## Local setup

Use Python 3.11, which is also used by the Docker image.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is then available at `http://127.0.0.1:8000`. The default `.env.example`
uses memory stores and does not require Redis or PostgreSQL to answer requests.

## Memory mode

Memory mode is the default and is useful for local review and tests:

```dotenv
FEATURE_STORE_TYPE=memory
CAMPAIGN_STORE_TYPE=memory
```

Known sample users and campaigns are defined in `app/feature_store.py` and
`app/campaign_store.py`. Unknown users receive default features with
`is_default=True`, which is also noted in the decision reason.

Campaign spend is kept in the application process and resets on restart.
Decision logging still makes a best-effort PostgreSQL write; a missing database
does not fail the request.

## Docker Compose setup

The Compose file defines services named `app`, `redis`, and `postgres`. It runs
the app with Redis user features and PostgreSQL campaigns:

```bash
docker compose up --build
```

The service is exposed on port `8000`, Redis on `6379`, and PostgreSQL on
`5432`. Compose starts the dependencies but does not initialize tables or seed
data; run the following scripts after PostgreSQL is accepting connections.

## PostgreSQL initialization

Create the `campaigns` and `bid_decisions` tables:

```bash
docker compose exec app python scripts/init_db.py
```

For a locally installed PostgreSQL instance, set `DATABASE_URL` and run:

```bash
python scripts/init_db.py
```

## PostgreSQL campaign seeding

Insert or update the sample campaigns after table initialization:

```bash
docker compose exec app python scripts/seed_postgres.py
```

The local equivalent is:

```bash
python scripts/seed_postgres.py
```

Seeding uses SQLAlchemy `merge`, so rerunning the script updates the sample rows
by `campaign_id`.

## Redis feature seeding

Seed the sample user-feature JSON values under keys such as
`user_features:user_sports_1`:

```bash
docker compose exec app python scripts/seed_redis.py
```

With Redis running locally at the configured `REDIS_URL`:

```bash
python scripts/seed_redis.py
```

## Running tests

From the repository root:

```bash
PYTHONPATH=. python -m pytest -q
```

The tests use memory stores and fakes/mocks for Redis, PostgreSQL, and OpenAI;
they do not require those external services.

## Running the load test

Start the API first, then run:

```bash
python scripts/load_test.py
```

The script sends 100 requests to `http://127.0.0.1:8000/bid` with concurrency
10 and prints success counts, decision counts, throughput, and latency summary
statistics. Its URL, request count, and concurrency are constants in the script.

## `GET /health` example

Request:

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

This is a process health response; it does not probe Redis or PostgreSQL.

## `GET /metrics` example

Request:

```http
GET /metrics
```

Example response from a fresh process:

```json
{
  "total_requests": 0,
  "bid_count": 0,
  "no_bid_count": 0,
  "average_latency_ms": 0.0
}
```

These counters cover completed `/bid` requests only. They are held in memory
and reset when the app process restarts.

## `POST /bid` BID example

Request:

```http
POST /bid
Content-Type: application/json

{
  "impression_id": "imp_123",
  "user_id": "user_sports_1",
  "placement": "mobile_feed",
  "country": "IL",
  "device": "mobile",
  "floor_price": 1.2,
  "context": "sports shoes sale"
}
```

Response with the default memory data and scoring configuration:

```json
{
  "impression_id": "imp_123",
  "decision": "BID",
  "bid_price": 2.45,
  "creative_id": "creative_sports_001",
  "experiment_group": "B",
  "score": 0.835,
  "reason": "High predicted value and bid price is above floor price"
}
```

## `POST /bid` NO_BID example

The same opportunity is rejected when its floor price exceeds the calculated
bid:

```http
POST /bid
Content-Type: application/json

{
  "impression_id": "imp_124",
  "user_id": "user_sports_1",
  "placement": "mobile_feed",
  "country": "IL",
  "device": "mobile",
  "floor_price": 20.0,
  "context": "sports shoes sale"
}
```

```json
{
  "impression_id": "imp_124",
  "decision": "NO_BID",
  "bid_price": null,
  "creative_id": null,
  "experiment_group": "B",
  "score": 0.835,
  "reason": "Calculated bid price is below floor price"
}
```

## Scoring logic

The service derives three bounded signals:

```text
ctr_signal = clamp(user_ctr / MAX_CTR, 0, 1)
user_value = clamp(user_value, 0, 1)

context_score = 0.35  when the category is unknown
                1.00  when user segment equals the category
                0.55  when the user segment is unknown
                0.65  otherwise
```

The final score is rounded to four decimal places:

```text
score = 0.45 * ctr_signal + 0.35 * user_value + 0.20 * context_score
```

The candidate bid is rounded to two decimal places:

```text
multiplier = BID_MULTIPLIER
multiplier *= GROUP_B_BID_MULTIPLIER  for group B

candidate_bid = 0.30 + score * user_value * multiplier * 2.0
```

A campaign is considered only when the score meets the experiment threshold and
the candidate bid meets the request's `floor_price`. The final bid is
`min(candidate_bid, campaign.max_bid)`.

## A/B testing

The service hashes `user_id` with SHA-256, converts the first eight hexadecimal
characters to a bucket from 0 to 99, and assigns:

- Group A for buckets 0-49
- Group B for buckets 50-99

The assignment is stable across processes. Group A uses `BID_THRESHOLD`. Group B
uses `BID_THRESHOLD + GROUP_B_THRESHOLD_DELTA` and multiplies its bid multiplier
by `GROUP_B_BID_MULTIPLIER`.

## Campaign eligibility rules

A campaign is eligible when all of the following are true:

- `status` is `active`
- `target_country` exactly matches the request `country`
- `target_device` exactly matches the request `device`
- `target_placement` exactly matches the request `placement`
- `category` matches the classified category or is `generic`
- `spent_today` is less than `daily_budget`
- `max_bid` is at least the request `floor_price`

PostgreSQL prefers exact-category campaigns over `generic` campaigns, then
orders by `campaign_id`. The memory store returns the first eligible item in its
list. If no campaign is eligible, the response reason is `No eligible campaign
found`.

## Campaign budget accounting

After producing a `BID`, the service attempts to add the final capped bid price
to the selected campaign's `spent_today` value. The memory store protects the
update with a lock. PostgreSQL uses a conditional atomic update that refuses to
cross `daily_budget`.

The spend write is best-effort: a rejected update, race, or database failure does
not alter the already-created API response. `NO_BID` responses never update
spend. Resetting `spent_today` for a new day is assumed to be handled outside
this service.

## Bid decision logging

For each validated request that reaches a decision, the service attempts to
insert a row into PostgreSQL's `bid_decisions` table. The row contains:

- Impression, user, placement, country, device, floor price, and context
- Classified category, experiment group, score, and decision
- Bid price, creative ID, campaign ID, reason, and creation time

Logging is best-effort. Connection or write failures do not change the API
response. Validation failures are returned before a decision exists and are not
logged.

## Optional OpenAI enrichment and fallback

Local keyword classification is the default. Supported output categories are
`sports`, `finance`, `fashion`, `gaming`, `travel`, `generic`, and `unknown`.

Enable OpenAI classification with:

```dotenv
ENABLE_AI_ENRICHMENT=true
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=1.0
```

The service uses the OpenAI Chat Completions API with temperature 0. It uses the
local classification when enrichment is disabled, the key is empty, context is
empty, the request times out or raises an exception, the response has no text,
or the model returns an unsupported category. AI errors are not exposed in the
API response.

## Configuration reference

Settings are read from environment variables and an optional local `.env` file.

| Variable | Default | Purpose |
|---|---:|---|
| `BID_THRESHOLD` | `0.65` | Group A minimum score |
| `BID_MULTIPLIER` | `1.4` | Base bid-price multiplier |
| `GROUP_B_THRESHOLD_DELTA` | `0.03` | Amount added to the group B threshold |
| `GROUP_B_BID_MULTIPLIER` | `1.08` | Additional group B bid multiplier |
| `MAX_CTR` | `0.12` | CTR value that normalizes to a signal of 1 |
| `FEATURE_STORE_TYPE` | `memory` | Use `redis` for Redis; otherwise memory is used |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CAMPAIGN_STORE_TYPE` | `memory` | Use `postgres` for PostgreSQL; otherwise memory is used |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/bid_service` | SQLAlchemy database URL for campaigns and logs |
| `ENABLE_AI_ENRICHMENT` | `false` | Enable optional OpenAI classification |
| `OPENAI_API_KEY` | empty | OpenAI credential; never commit a real value |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat Completions model name |
| `AI_TIMEOUT_SECONDS` | `1.0` | OpenAI client/request timeout |

Accepted request values are:

- `placement`: `mobile_feed`, `desktop_banner`, or `video_pre_roll`
- `device`: `mobile`, `desktop`, or `tablet`
- `country`: any two-character string
- `floor_price`: a number greater than or equal to zero
- `context`: an optional string

`impression_id` and `user_id` must be non-empty strings.

Every response contains `impression_id`, `decision`, `bid_price`, `creative_id`,
`experiment_group`, `score`, and `reason`. The bid and creative fields are
`null` for `NO_BID`.

## Error handling and graceful degradation

- Invalid request bodies receive FastAPI's standard `422` validation response.
- Redis misses, invalid JSON, timeouts, and connection errors use default user
  features and continue.
- A PostgreSQL campaign query failure behaves like no eligible campaign and
  returns `NO_BID`.
- Campaign spend and decision-log write failures are ignored after the decision
  is created.
- OpenAI is never required; all AI failures use local classification.
- `/health` reports application availability only and does not guarantee that
  Redis or PostgreSQL is reachable.

## Assumptions and trade-offs

- Runtime metrics and memory-store state are process-local and are not shared
  across workers.
- The service does not reset daily budgets or perform time-zone-aware pacing.
- Campaign selection is deterministic but intentionally simple; it does not
  optimize across multiple eligible campaigns.
- PostgreSQL spend is guarded against exceeding the daily budget, but the API
  response is not rolled back if that post-decision write loses a race or fails.
- Synchronous OpenAI classification is suitable only as an optional demo path,
  not as the default dependency of a strict low-latency bidder.
- The sample `campaign_budget` field in user features is retained as input data
  but is not used by the scoring or campaign-budget logic.

## Production improvements

Outside the assignment scope, a production service could add shared metrics and
tracing, explicit dependency readiness checks, retries or circuit breakers,
idempotency, stronger transaction boundaries around spend, scheduled budget
resets, caching, and multi-worker-safe state.

At larger scale, Kafka could decouple event processing, Kubernetes could manage
deployment and scaling, a trained ML model could replace the heuristic score,
and advanced pacing could distribute campaign budget across the day. Those are
deliberately not implemented here.

## How AI tools were used during development

AI tools were used as development assistants for implementation review, test
ideas, and documentation drafting. Their output was checked against the source
code and verified with the repository's test suite. No runtime AI dependency is
required: OpenAI enrichment remains disabled by default and has a local
fallback.
