from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)


def make_bid_payload(impression_id="imp_123", floor_price=1.2):
    return {
        "impression_id": impression_id,
        "user_id": "user_sports_1",
        "placement": "mobile_feed",
        "country": "IL",
        "device": "mobile",
        "floor_price": floor_price,
        "context": "sports shoes sale",
    }


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bid_endpoint_returns_valid_bid_response():
    payload = make_bid_payload()

    response = client.post("/bid", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["impression_id"] == "imp_123"
    assert data["decision"] in {"BID", "NO_BID"}
    assert data["experiment_group"] in {"A", "B"}
    assert 0 <= data["score"] <= 1
    assert "reason" in data


def test_successful_bid_updates_campaign_spend(monkeypatch):
    from app.campaign_store import MemoryCampaignStore, SAMPLE_CAMPAIGNS

    campaign = SAMPLE_CAMPAIGNS[0].copy()
    campaign["spent_today"] = 10.0
    campaign["max_bid"] = 1.5
    store = MemoryCampaignStore([campaign])
    monkeypatch.setattr(main_module, "get_campaign_store", lambda: store)
    monkeypatch.setattr(main_module, "log_bid_decision", lambda **kwargs: True)

    response = client.post("/bid", json=make_bid_payload("imp_spend_success"))

    assert response.status_code == 200
    assert response.json()["decision"] == "BID"
    assert response.json()["bid_price"] == 1.5
    assert campaign["spent_today"] == 11.5


def test_no_bid_does_not_update_campaign_spend(monkeypatch):
    class TrackingCampaignStore:
        def __init__(self):
            self.record_spend_calls = []

        def get_eligible_campaign(self, request, category, bid_price=None):
            return None

        def record_spend(self, campaign_id, amount):
            self.record_spend_calls.append((campaign_id, amount))
            return True

    store = TrackingCampaignStore()
    monkeypatch.setattr(main_module, "get_campaign_store", lambda: store)
    monkeypatch.setattr(main_module, "log_bid_decision", lambda **kwargs: True)

    response = client.post(
        "/bid",
        json=make_bid_payload("imp_no_spend", floor_price=100.0),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "NO_BID"
    assert store.record_spend_calls == []


def test_bid_endpoint_survives_spend_database_failure(monkeypatch):
    class FailingCampaignStore:
        def get_eligible_campaign(self, request, category, bid_price=None):
            return {
                "campaign_id": "campaign_sports_il_mobile",
                "max_bid": 1.5,
                "creative_id": "creative_sports_001",
            }

        def record_spend(self, campaign_id, amount):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        main_module,
        "get_campaign_store",
        lambda: FailingCampaignStore(),
    )
    monkeypatch.setattr(main_module, "log_bid_decision", lambda **kwargs: True)

    response = client.post("/bid", json=make_bid_payload("imp_spend_failure"))

    assert response.status_code == 200
    assert response.json()["decision"] == "BID"
    assert response.json()["bid_price"] == 1.5


def test_bid_endpoint_logs_decision_with_campaign_metadata(monkeypatch):
    logged = {}

    def fake_log_bid_decision(**kwargs):
        logged.update(kwargs)
        return True

    monkeypatch.setattr(main_module, "log_bid_decision", fake_log_bid_decision)

    response = client.post(
        "/bid",
        json={
            "impression_id": "imp_logged",
            "user_id": "user_sports_1",
            "placement": "mobile_feed",
            "country": "IL",
            "device": "mobile",
            "floor_price": 1.2,
            "context": "sports shoes sale",
        },
    )

    assert response.status_code == 200
    assert logged["request"].impression_id == "imp_logged"
    assert logged["response"].decision == "BID"
    assert logged["category"] == "sports"
    assert logged["campaign_id"] == "campaign_sports_il_mobile"


def test_bid_endpoint_survives_logging_failure(monkeypatch):
    def fail_to_log(**kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main_module, "log_bid_decision", fail_to_log)

    response = client.post(
        "/bid",
        json={
            "impression_id": "imp_log_failure",
            "user_id": "user_sports_1",
            "placement": "mobile_feed",
            "country": "IL",
            "device": "mobile",
            "floor_price": 1.2,
            "context": "sports shoes sale",
        },
    )

    assert response.status_code == 200
    assert response.json()["impression_id"] == "imp_log_failure"


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
