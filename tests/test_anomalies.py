# PROMPT: Test anomaly detection for queue spikes, conversion drops, and dead zones.
# CHANGES MADE: Anomaly endpoint tests with synthetic traffic patterns.

from __future__ import annotations

from helpers import make_event


def test_queue_spike_anomaly(client):
    events = []
    for i in range(10):
        events.append(
            make_event(
                visitor_id=f"vq-{i}",
                event_type="BILLING_QUEUE_JOIN",
                zone_id="billing_queue",
                metadata={"queue_depth": 8},
            )
        )
    client.post("/events/ingest", json={"events": events})
    anomalies = client.get("/stores/ST1008/anomalies").json()
    types = {a["anomaly_type"] for a in anomalies["anomalies"]}
    assert "QUEUE_SPIKE" in types


def test_conversion_drop_anomaly(client):
    for i in range(8):
        client.post(
            "/events/ingest",
            json={"events": [make_event(visitor_id=f"vc-{i}", event_type="ENTRY")]},
        )
    anomalies = client.get("/stores/ST1008/anomalies").json()
    types = {a["anomaly_type"] for a in anomalies["anomalies"]}
    assert "CONVERSION_DROP" in types


def test_dead_zone_anomaly(client):
    events = [make_event(event_type="ZONE_ENTER", zone_id="makeup") for _ in range(20)]
    events += [make_event(event_type="ZONE_ENTER", zone_id="rare_zone") for _ in range(1)]
    client.post("/events/ingest", json={"events": events})
    anomalies = client.get("/stores/ST1008/anomalies").json()
    types = {a["anomaly_type"] for a in anomalies["anomalies"]}
    assert "DEAD_ZONE" in types
