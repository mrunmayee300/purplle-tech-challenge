# PROMPT: Test session-based funnel without double counting across stages.
# CHANGES MADE: Funnel stage counts and dropoff validation tests.

from __future__ import annotations

from helpers import make_event


def test_funnel_stages(client):
    visitors = ["va", "vb", "vc"]
    events = []
    for v in visitors:
        events.append(make_event(visitor_id=v, event_type="ENTRY"))
        events.append(make_event(visitor_id=v, event_type="ZONE_ENTER", zone_id="makeup"))
    events.append(
        make_event(visitor_id="va", event_type="BILLING_QUEUE_JOIN", zone_id="billing_queue")
    )
    client.post("/events/ingest", json={"events": events})
    funnel = client.get("/stores/ST1008/funnel").json()
    stages = {s["stage"]: s["count"] for s in funnel["stages"]}
    assert stages["Entry"] == 3
    assert stages["Zone Visit"] == 3
    assert stages["Billing Queue"] == 1


def test_funnel_no_double_count(client):
    events = [
        make_event(visitor_id="vx", event_type="ENTRY"),
        make_event(visitor_id="vx", event_type="ENTRY"),
        make_event(visitor_id="vx", event_type="ZONE_ENTER", zone_id="makeup"),
        make_event(visitor_id="vx", event_type="ZONE_ENTER", zone_id="skincare"),
    ]
    client.post("/events/ingest", json={"events": events})
    funnel = client.get("/stores/ST1008/funnel").json()
    entry = next(s for s in funnel["stages"] if s["stage"] == "Entry")
    zone = next(s for s in funnel["stages"] if s["stage"] == "Zone Visit")
    assert entry["count"] == 1
    assert zone["count"] == 1
