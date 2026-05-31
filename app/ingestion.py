from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import EventRecord, SessionRecord
from app.schemas import EventIn, IngestResponse, IngestResultItem
from shared.events import StoreEvent

logger = logging.getLogger(__name__)


def _upsert_session(db: Session, event: EventIn) -> None:
    if event.is_staff:
        return
    session = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == event.store_id,
            SessionRecord.visitor_id == event.visitor_id,
            SessionRecord.ended_at.is_(None),
        )
        .order_by(SessionRecord.started_at.desc())
        .first()
    )
    et = event.event_type.upper()
    if et == "REENTRY" and session and session.ended_at is not None:
        session = None
    if et in ("ENTRY", "REENTRY") and session is None:
        session = SessionRecord(
            session_id=f"{event.store_id}:{event.visitor_id}:{event.event_id[:8]}",
            store_id=event.store_id,
            visitor_id=event.visitor_id,
            started_at=event.timestamp,
            is_staff=event.is_staff,
            zones_visited=[],
        )
        db.add(session)
    elif session is None:
        return

    zones = list(session.zones_visited or [])
    if event.zone_id and event.zone_id not in zones:
        zones.append(event.zone_id)
    session.zones_visited = zones

    if et == "BILLING_QUEUE_JOIN":
        session.queue_joined = True
    if et == "EXIT":
        session.ended_at = event.timestamp
    db.add(session)


def ingest_events(db: Session, events: list[EventIn]) -> IngestResponse:
    accepted = duplicate = failed = 0
    results: list[IngestResultItem] = []

    for raw in events:
        try:
            validated = StoreEvent(**raw.model_dump())
        except Exception as exc:
            failed += 1
            results.append(
                IngestResultItem(
                    event_id=raw.event_id, status="failed", error=str(exc)
                )
            )
            continue

        existing = (
            db.query(EventRecord).filter(EventRecord.event_id == validated.event_id).first()
        )
        if existing:
            duplicate += 1
            results.append(IngestResultItem(event_id=validated.event_id, status="duplicate"))
            continue

        record = EventRecord(
            event_id=validated.event_id,
            store_id=validated.store_id,
            camera_id=validated.camera_id,
            visitor_id=validated.visitor_id,
            event_type=validated.event_type,
            timestamp=validated.timestamp,
            zone_id=validated.zone_id,
            dwell_ms=validated.dwell_ms,
            is_staff=validated.is_staff,
            confidence=validated.confidence,
            metadata_json=validated.metadata,
        )
        try:
            db.add(record)
            db.flush()
            _upsert_session(db, raw)
            accepted += 1
            results.append(IngestResultItem(event_id=validated.event_id, status="accepted"))
        except IntegrityError:
            db.rollback()
            duplicate += 1
            results.append(
                IngestResultItem(event_id=validated.event_id, status="duplicate")
            )
        except Exception as exc:
            db.rollback()
            failed += 1
            results.append(
                IngestResultItem(
                    event_id=validated.event_id, status="failed", error=str(exc)
                )
            )

    if accepted:
        db.commit()
    else:
        db.commit()

    return IngestResponse(
        accepted=accepted,
        duplicate=duplicate,
        failed=failed,
        results=results,
    )


def last_event_timestamp(db: Session, store_id: str | None = None) -> datetime | None:
    q = db.query(EventRecord).order_by(EventRecord.timestamp.desc())
    if store_id:
        q = q.filter(EventRecord.store_id == store_id)
    row = q.first()
    return row.timestamp if row else None


def is_feed_stale(db: Session, threshold_minutes: int | None = None) -> bool:
    import os

    from sqlalchemy import func

    from app.models import EventRecord

    count = db.query(func.count(EventRecord.id)).scalar() or 0
    if count == 0:
        return True

    if os.getenv("DEMO_MODE", "1") == "1":
        # Batch CCTV + POS challenge: anchored timestamps are expected, not "live".
        return False

    if threshold_minutes is None:
        threshold_minutes = int(os.getenv("STALE_FEED_MINUTES", "30"))

    last = last_event_timestamp(db)
    if last is None:
        return True
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() > threshold_minutes * 60
