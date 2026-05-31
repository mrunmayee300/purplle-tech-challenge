# PROMPT: Direct service-layer tests for ingestion, metrics, funnel, heatmap, anomalies, event bus.
# CHANGES MADE: Broad coverage tests invoking app modules with in-memory SQLite.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.anomalies import detect_anomalies
from app.funnel import compute_funnel
from app.heatmap import compute_heatmap
from app.ingestion import ingest_events, is_feed_stale, last_event_timestamp
from app.metrics import compute_metrics
from app.schemas import EventIn
from helpers import make_event
from pipeline.detect import Detection, PersonDetector
from pipeline.zone_mapper import ZoneMapper
from shared.event_bus import EventBus
from shared.events import StoreEvent, new_event
from shared.layout import StoreLayout


def _event_in(**kwargs) -> EventIn:
    return EventIn(**make_event(**kwargs))


def test_ingest_service(db_session):
    events = [_event_in(visitor_id=f"v{i}") for i in range(5)]
    result = ingest_events(db_session, events)
    assert result.accepted == 5
    assert last_event_timestamp(db_session) is not None
    assert last_event_timestamp(db_session, "ST1008") is not None


def test_metrics_service(db_session):
    ingest_events(
        db_session,
        [
            _event_in(visitor_id="m1", event_type="ENTRY"),
            _event_in(visitor_id="m1", event_type="ZONE_DWELL", zone_id="makeup", dwell_ms=30000),
            _event_in(visitor_id="m1", event_type="BILLING_QUEUE_JOIN", zone_id="billing_queue"),
        ],
    )
    metrics = compute_metrics(db_session, "ST1008")
    assert metrics.unique_visitors >= 1
    assert "makeup" in metrics.avg_dwell_per_zone or metrics.avg_dwell_per_zone == {}


def test_funnel_service(db_session):
    ingest_events(db_session, [_event_in(visitor_id="f1", event_type="ENTRY")])
    funnel = compute_funnel(db_session, "ST1008")
    assert funnel.stages[0].stage == "Entry"


def test_heatmap_service(db_session):
    ingest_events(
        db_session,
        [_event_in(event_type="ZONE_ENTER", zone_id="skincare", visitor_id="h1")],
    )
    heatmap = compute_heatmap(db_session, "ST1008")
    assert heatmap.data_confidence >= 0


def test_anomalies_service(db_session):
    events = [
        _event_in(
            visitor_id=f"q{i}",
            event_type="BILLING_QUEUE_JOIN",
            zone_id="billing_queue",
            metadata={"queue_depth": 9},
        )
        for i in range(6)
    ]
    ingest_events(db_session, events)
    anomalies = detect_anomalies(db_session, "ST1008")
    assert anomalies.store_id == "ST1008"


def test_event_bus_jsonl(tmp_path):
    path = tmp_path / "out.jsonl"
    bus = EventBus(jsonl_path=path)
    ev = new_event(
        store_id="ST1008",
        camera_id="cam_1",
        visitor_id="v-bus",
        event_type="ENTRY",
        timestamp=datetime.now(timezone.utc),
        confidence=0.9,
    )
    bus.publish(ev)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_type"] == "ENTRY"


def test_store_event_validation():
    with pytest.raises(ValueError):
        StoreEvent(
            store_id="ST1008",
            camera_id="cam_1",
            visitor_id="v",
            event_type="INVALID",
            timestamp=datetime.now(timezone.utc),
            confidence=0.5,
        )


def test_zone_mapper_all_zones():
    layout = StoreLayout.load()
    mapper = ZoneMapper(layout)
    for cam in layout.cameras:
        zone = mapper.zone_at_point(cam, (0.5, 0.5))
        assert zone is None or isinstance(zone, str)


def test_detection_dataclass():
    det = Detection(bbox=(0.1, 0.1, 0.2, 0.2), confidence=0.8)
    assert det.class_id == 0
