# PROMPT: Test health endpoint and database unavailable handling.
# CHANGES MADE: Health status tests and structured 503 validation.

from __future__ import annotations

from unittest.mock import patch

from helpers import make_event


def test_health_ok(client):
    client.post("/events/ingest", json={"events": [make_event()]})
    health = client.get("/health").json()
    assert health["database"] == "up"
    assert health["last_event_timestamp"] is not None


def test_database_unavailable_returns_503(client):
    with patch("app.main.database_available", return_value=False):
        response = client.get("/stores/ST1008/metrics")
    assert response.status_code == 503
    assert "database_unavailable" in response.json()["detail"]["error"]
