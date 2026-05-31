# PROMPT:
# Validate ingestion API — batch limits (500), deduplication, idempotent re-post,
# partial success on invalid UUID, and duplicate event_id in same batch.
#
# CHANGES MADE:
# Full ingestion test suite; max batch expects 400/422; edge duplicate batch test added.

from __future__ import annotations

import uuid

import pytest

from helpers import make_event


def test_ingest_accepts_valid_events(client):
    events = [make_event(visitor_id=f"v-{i}") for i in range(3)]
    response = client.post("/events/ingest", json={"events": events})
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 3
    assert body["failed"] == 0


def test_ingest_deduplication(client):
    event = make_event()
    first = client.post("/events/ingest", json={"events": [event]})
    second = client.post("/events/ingest", json={"events": [event]})
    assert first.json()["accepted"] == 1
    assert second.json()["duplicate"] == 1


def test_ingest_partial_success(client):
    good = make_event()
    bad = make_event(event_id="not-a-uuid")
    response = client.post("/events/ingest", json={"events": [good, bad]})
    body = response.json()
    assert body["accepted"] == 1
    assert body["failed"] == 1


def test_ingest_max_batch(client):
    events = [make_event(visitor_id=f"v-{i}") for i in range(501)]
    response = client.post("/events/ingest", json={"events": events})
    assert response.status_code in (400, 422)


def test_idempotent_ingest(client):
    event = make_event(visitor_id="v-idem")
    assert client.post("/events/ingest", json={"events": [event]}).json()["accepted"] == 1
    second = client.post("/events/ingest", json={"events": [event]}).json()
    assert second["duplicate"] == 1
    assert second["accepted"] == 0


def test_duplicate_events_edge_case(client):
    eid = str(uuid.uuid4())
    events = [
        make_event(event_id=eid, visitor_id="v-dup-a"),
        make_event(event_id=eid, visitor_id="v-dup-b"),
    ]
    body = client.post("/events/ingest", json={"events": events}).json()
    assert body["accepted"] == 1
    assert body["duplicate"] == 1
