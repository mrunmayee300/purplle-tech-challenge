# PROMPT: Edge cases — empty store, all staff, re-entry, duplicate events, zero purchases, queue abandonment.
# CHANGES MADE: Consolidated edge-case API tests per challenge requirements.

from __future__ import annotations

from datetime import datetime, timezone

from helpers import make_event


def test_empty_store(client):
    metrics = client.get("/stores/ST1008/metrics").json()
    funnel = client.get("/stores/ST1008/funnel").json()
    assert metrics["unique_visitors"] == 0
    assert funnel["stages"][0]["count"] == 0


def test_all_staff_clip(client):
    events = [
        make_event(visitor_id="staff-a", event_type="ENTRY", is_staff=True),
        make_event(visitor_id="staff-a", event_type="ZONE_ENTER", zone_id="makeup", is_staff=True),
        make_event(visitor_id="staff-b", event_type="ENTRY", is_staff=True),
    ]
    client.post("/events/ingest", json={"events": events})
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["unique_visitors"] == 0


def test_reentry_event(client):
    events = [
        make_event(visitor_id="v-re", event_type="ENTRY"),
        make_event(
            visitor_id="v-re",
            event_type="EXIT",
            zone_id="exit_lane",
            timestamp=datetime(2026, 4, 10, 12, 10, 0, tzinfo=timezone.utc).isoformat(),
        ),
        make_event(
            visitor_id="v-re",
            event_type="REENTRY",
            timestamp=datetime(2026, 4, 10, 12, 20, 0, tzinfo=timezone.utc).isoformat(),
        ),
    ]
    client.post("/events/ingest", json={"events": events})
    funnel = client.get("/stores/ST1008/funnel").json()
    assert funnel["stages"][0]["count"] == 1


def test_queue_abandonment(client):
    events = [
        make_event(visitor_id="v-abn", event_type="ENTRY"),
        make_event(
            visitor_id="v-abn",
            event_type="BILLING_QUEUE_JOIN",
            zone_id="billing_queue",
        ),
        make_event(
            visitor_id="v-abn",
            event_type="BILLING_QUEUE_ABANDON",
            zone_id="billing_queue",
        ),
    ]
    body = client.post("/events/ingest", json={"events": events}).json()
    assert body["accepted"] == 3
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["abandonment_rate"] > 0


def test_zero_purchases(client):
    for i in range(4):
        client.post(
            "/events/ingest",
            json={
                "events": [
                    make_event(visitor_id=f"zp-{i}", event_type="ENTRY"),
                    make_event(
                        visitor_id=f"zp-{i}",
                        event_type="BILLING_QUEUE_JOIN",
                        zone_id="billing_queue",
                        timestamp=datetime(2026, 4, 10, 15, i, 0, tzinfo=timezone.utc).isoformat(),
                    ),
                ]
            },
        )
    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["conversion_rate"] == 0.0
