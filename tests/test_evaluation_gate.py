# PROMPT: Acceptance-gate tests aligned with Purplle evaluation framework.
# CHANGES MADE: /metrics alias, health demo mode, bootstrap idempotency checks.

from __future__ import annotations

from helpers import make_event


def test_metrics_alias_endpoints(client):
    for path in ("/metrics", "/Metrics"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["store_id"] == "ST1008"
        assert "unique_visitors" in body
        assert "conversion_rate" in body


def test_health_healthy_with_events(client):
    client.post("/events/ingest", json={"events": [make_event()]})
    health = client.get("/health").json()
    assert health["database"] == "up"
    assert health["status"] in ("healthy", "degraded")
    assert health["stale_feed"] is False
