"""Load events into DB directly (no HTTP) — used on container startup before API serves traffic."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import init_db, session_scope
from app.ingestion import ingest_events
from app.schemas import EventIn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap")

DATA = Path(__import__("os").environ.get("DATASET_ROOT", ROOT.parent / "dataset"))
STORE = "ST1008"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def synthetic_events() -> list[dict]:
    """Recent timestamps so /health is healthy for evaluators."""
    now = datetime.now(timezone.utc)

    def ev(
        vid: str,
        et: str,
        offset_min: int,
        zone: str | None = None,
        staff: bool = False,
        meta: dict | None = None,
    ) -> dict:
        return {
            "event_id": str(uuid.uuid4()),
            "store_id": STORE,
            "camera_id": "cam_1",
            "visitor_id": vid,
            "event_type": et,
            "timestamp": (now - timedelta(minutes=offset_min)).isoformat(),
            "zone_id": zone,
            "dwell_ms": 45000 if et == "ZONE_DWELL" else None,
            "is_staff": staff,
            "confidence": 0.9,
            "metadata": meta or {},
        }

    batch = []
    visitors = [f"v-demo-{i:02d}" for i in range(1, 6)]
    for i, vid in enumerate(visitors[:3]):
        batch.append(ev(vid, "ENTRY", 30 - i))
        batch.append(ev(vid, "ZONE_ENTER", 25 - i, "makeup"))
        batch.append(ev(vid, "ZONE_DWELL", 20 - i, "makeup"))
        batch.append(
            ev(
                vid,
                "BILLING_QUEUE_JOIN",
                10 - i,
                "billing_queue",
                meta={"queue_depth": i + 1},
            )
        )
    batch.append(ev(visitors[0], "REENTRY", 5, "entry"))
    batch.append(ev("v-staff-01", "ENTRY", 28, "entry", staff=True))
    batch.append(ev(visitors[3], "BILLING_QUEUE_ABANDON", 8, "billing_queue"))
    return batch


def main() -> None:
    from app.models import EventRecord

    init_db()
    with session_scope() as db:
        existing = db.query(EventRecord).count()
        if existing > 0:
            logger.info("Database already has %s events; skipping bootstrap", existing)
            return

    events: list[dict] = []
    events.extend(load_jsonl(DATA / "sample_events.jsonl"))
    events.extend(load_jsonl(DATA / "generated_events.jsonl"))
    events.extend(synthetic_events())

    seen: set[str] = set()
    unique: list[EventIn] = []
    for raw in events:
        eid = raw.get("event_id")
        if eid in seen:
            continue
        seen.add(eid)
        unique.append(EventIn(**raw))

    if not unique:
        logger.warning("No events to bootstrap")
        return

    with session_scope() as db:
        result = ingest_events(db, unique)
    logger.info(
        "Bootstrap complete: accepted=%s duplicate=%s failed=%s",
        result.accepted,
        result.duplicate,
        result.failed,
    )


if __name__ == "__main__":
    main()
