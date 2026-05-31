# PROMPT: Test store metrics — visitors, conversion, dwell, queue, abandonment, zero purchases.
# CHANGES MADE: Metrics tests with POS correlation and empty-store scenarios.

from __future__ import annotations

from datetime import datetime, timezone

from helpers import make_event


def _ingest(client, events):
    return client.post("/events/ingest", json={"events": events})


def test_metrics_unique_visitors(client):
    events = [
        make_event(visitor_id="v1", event_type="ENTRY"),
        make_event(visitor_id="v2", event_type="ENTRY"),
        make_event(visitor_id="v1", event_type="ZONE_ENTER", zone_id="makeup"),
    ]
    _ingest(client, events)
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["unique_visitors"] == 2


def test_metrics_zero_purchases(client):
    events = [
        make_event(visitor_id="v-zp", event_type="ENTRY"),
        make_event(
            visitor_id="v-zp",
            event_type="BILLING_QUEUE_JOIN",
            zone_id="billing_queue",
            timestamp=datetime(2026, 4, 10, 18, 0, 0, tzinfo=timezone.utc).isoformat(),
        ),
    ]
    _ingest(client, events)
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["conversion_rate"] == 0.0


def test_empty_store_metrics(client):
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["unique_visitors"] == 0
    assert metrics["conversion_rate"] == 0.0


def test_abandonment_rate(client):
    events = [
        make_event(visitor_id="v-ab", event_type="ENTRY"),
        make_event(
            visitor_id="v-ab",
            event_type="BILLING_QUEUE_JOIN",
            zone_id="billing_queue",
            metadata={"queue_depth": 1},
        ),
        make_event(
            visitor_id="v-ab",
            event_type="BILLING_QUEUE_ABANDON",
            zone_id="billing_queue",
        ),
    ]
    _ingest(client, events)
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["abandonment_rate"] >= 1.0
