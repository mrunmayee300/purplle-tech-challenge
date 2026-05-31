"""Seed API database from sample_events.jsonl and synthetic edge-case events."""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

DATA = Path("/data") if Path("/data").exists() else Path(__file__).resolve().parents[2] / "dataset"
API = __import__("os").environ.get("API_BASE_URL", "http://localhost:8000")
STORE = "ST1008"


def load_jsonl(path: Path) -> list[dict]:
    events = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def synthetic_events() -> list[dict]:
    base = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    visitors = [f"v-test-{i:03d}" for i in range(1, 8)]

    def ev(vid: str, et: str, minutes: int, zone: str | None = None, staff: bool = False, meta=None):
        return {
            "event_id": str(uuid.uuid4()),
            "store_id": STORE,
            "camera_id": "cam_1",
            "visitor_id": vid,
            "event_type": et,
            "timestamp": (base.replace(minute=0) + __import__("datetime").timedelta(minutes=minutes)).isoformat(),
            "zone_id": zone,
            "dwell_ms": 45000 if et == "ZONE_DWELL" else None,
            "is_staff": staff,
            "confidence": 0.9,
            "metadata": meta or {},
        }

    batch = []
    for vid in visitors[:3]:
        batch.append(ev(vid, "ENTRY", 10, "entry"))
        batch.append(ev(vid, "ZONE_ENTER", 15, "makeup"))
        batch.append(ev(vid, "ZONE_DWELL", 20, "makeup"))
        batch.append(ev(vid, "BILLING_QUEUE_JOIN", 40, "billing_queue", meta={"queue_depth": 2}))
    batch.append(ev(visitors[0], "REENTRY", 55, "entry"))
    batch.append(ev("v-staff-01", "ENTRY", 5, "entry", staff=True))
    batch.append(ev("v-staff-01", "ZONE_ENTER", 30, "skincare", staff=True))
    batch.append(ev(visitors[3], "BILLING_QUEUE_JOIN", 42, "billing_queue"))
    batch.append(ev(visitors[3], "BILLING_QUEUE_ABANDON", 48, "billing_queue"))
    batch.append(ev(visitors[4], "EXIT", 60, "exit_lane"))
    return batch


def main() -> None:
    events = load_jsonl(DATA / "sample_events.jsonl")
    generated = DATA / "generated_events.jsonl"
    events.extend(load_jsonl(generated))
    events.extend(synthetic_events())

    # dedupe by event_id
    seen = set()
    unique = []
    for e in events:
        if e["event_id"] not in seen:
            seen.add(e["event_id"])
            unique.append(e)

    for i in range(0, len(unique), 100):
        chunk = unique[i : i + 100]
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(10):
                try:
                    r = client.post(f"{API}/events/ingest", json={"events": chunk})
                    r.raise_for_status()
                    print(r.json())
                    break
                except Exception as exc:
                    if attempt == 9:
                        print(f"Seed failed: {exc}", file=sys.stderr)
                        sys.exit(1)
                    __import__("time").sleep(3)
    print(f"Seeded {len(unique)} events")


if __name__ == "__main__":
    main()
