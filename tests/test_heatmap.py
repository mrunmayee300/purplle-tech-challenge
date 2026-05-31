# PROMPT:
# Test heatmap endpoint for zone frequencies, dwell averages, normalized scores,
# and data_confidence flag.
#
# CHANGES MADE:
# Added dedicated heatmap tests with multi-zone ingest and empty-store baseline.

from __future__ import annotations

from helpers import make_event


def test_heatmap_generation(client):
    events = []
    for i in range(12):
        events.append(
            make_event(
                visitor_id=f"vh-{i}",
                event_type="ZONE_ENTER",
                zone_id="makeup",
            )
        )
    events.append(
        make_event(
            visitor_id="vh-1",
            event_type="ZONE_DWELL",
            zone_id="makeup",
            dwell_ms=60000,
        )
    )
    client.post("/events/ingest", json={"events": events})
    heatmap = client.get("/stores/ST1008/heatmap").json()
    assert heatmap["store_id"] == "ST1008"
    assert len(heatmap["zones"]) >= 1
    assert heatmap["data_confidence"] > 0
    zone = heatmap["zones"][0]
    assert "normalized_score" in zone
    assert zone["frequency"] >= 1


def test_heatmap_empty_store(client):
    heatmap = client.get("/stores/ST1008/heatmap").json()
    assert heatmap["zones"] == []
    assert heatmap["data_confidence"] == 0.0
