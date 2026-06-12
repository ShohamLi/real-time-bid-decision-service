from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bid_endpoint_returns_valid_bid_response():
    payload = {
        "impression_id": "imp_123",
        "user_id": "user_sports_1",
        "placement": "mobile_feed",
        "country": "IL",
        "device": "mobile",
        "floor_price": 1.2,
        "context": "sports shoes sale",
    }

    response = client.post("/bid", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["impression_id"] == "imp_123"
    assert data["decision"] in {"BID", "NO_BID"}
    assert data["experiment_group"] in {"A", "B"}
    assert 0 <= data["score"] <= 1
    assert "reason" in data


def test_bid_endpoint_rejects_missing_user_id():
    payload = {
        "impression_id": "imp_123",
        "placement": "mobile_feed",
        "country": "IL",
        "device": "mobile",
        "floor_price": 1.2,
        "context": "sports shoes sale",
    }

    response = client.post("/bid", json=payload)

    assert response.status_code == 422


def test_bid_endpoint_rejects_invalid_floor_price():
    payload = {
        "impression_id": "imp_123",
        "user_id": "user_sports_1",
        "placement": "mobile_feed",
        "country": "IL",
        "device": "mobile",
        "floor_price": -1,
        "context": "sports shoes sale",
    }

    response = client.post("/bid", json=payload)

    assert response.status_code == 422


def test_bid_endpoint_rejects_unknown_placement():
    payload = {
        "impression_id": "imp_123",
        "user_id": "user_sports_1",
        "placement": "unknown_placement",
        "country": "IL",
        "device": "mobile",
        "floor_price": 1.2,
        "context": "sports shoes sale",
    }

    response = client.post("/bid", json=payload)

    assert response.status_code == 422


def test_metrics_endpoint_returns_runtime_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200

    data = response.json()
    assert "total_requests" in data
    assert "bid_count" in data
    assert "no_bid_count" in data
    assert "average_latency_ms" in data
