from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EventRecord, SessionRecord
from app.schemas import MetricsResponse
from shared.config import CONVERSION_LOOKBACK_MINUTES, POS_PATH


def _load_pos_transactions(store_id: str) -> list[dict]:
    if not POS_PATH.exists():
        return []
    rows = []
    with POS_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("store_id") != store_id:
                continue
            ts = datetime.fromisoformat(row["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            rows.append(row)
    return rows


def _mark_conversions(db: Session, store_id: str) -> None:
    pos_rows = _load_pos_transactions(store_id)
    lookback = timedelta(minutes=CONVERSION_LOOKBACK_MINUTES)
    sessions = (
        db.query(SessionRecord)
        .filter(SessionRecord.store_id == store_id, SessionRecord.is_staff.is_(False))
        .all()
    )
    for session in sessions:
        billing_events = (
            db.query(EventRecord)
            .filter(
                EventRecord.store_id == store_id,
                EventRecord.visitor_id == session.visitor_id,
                EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]),
                EventRecord.zone_id.in_(["billing", "billing_queue"]),
                EventRecord.is_staff.is_(False),
            )
            .all()
        )
        for pos in pos_rows:
            pos_ts = datetime.fromisoformat(pos["timestamp"])
            if pos_ts.tzinfo is None:
                pos_ts = pos_ts.replace(tzinfo=timezone.utc)
            for be in billing_events:
                be_ts = be.timestamp
                if be_ts.tzinfo is None:
                    be_ts = be_ts.replace(tzinfo=timezone.utc)
                if be_ts <= pos_ts <= be_ts + lookback:
                    session.converted = True
                    session.purchased = True
                    db.add(session)
                    break


def compute_metrics(db: Session, store_id: str) -> MetricsResponse:
    _mark_conversions(db, store_id)
    db.commit()

    visitors = (
        db.query(EventRecord.visitor_id)
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.is_staff.is_(False),
            EventRecord.event_type.in_(["ENTRY", "REENTRY"]),
        )
        .distinct()
        .count()
    )

    converted = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.is_staff.is_(False),
            SessionRecord.converted.is_(True),
        )
        .count()
    )
    conversion_rate = (converted / visitors) if visitors else 0.0

    dwell_rows = (
        db.query(
            EventRecord.zone_id,
            func.avg(EventRecord.dwell_ms),
        )
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "ZONE_DWELL",
            EventRecord.is_staff.is_(False),
            EventRecord.zone_id.isnot(None),
        )
        .group_by(EventRecord.zone_id)
        .all()
    )
    avg_dwell = {
        zone: round((ms or 0) / 1000.0, 2) for zone, ms in dwell_rows if zone
    }

    latest_queue = (
        db.query(EventRecord)
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "BILLING_QUEUE_JOIN",
        )
        .order_by(EventRecord.timestamp.desc())
        .first()
    )
    queue_depth = 0
    if latest_queue and latest_queue.metadata_json:
        queue_depth = int(latest_queue.metadata_json.get("queue_depth", 0))

    joins = (
        db.query(func.count(EventRecord.id))
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "BILLING_QUEUE_JOIN",
            EventRecord.is_staff.is_(False),
        )
        .scalar()
        or 0
    )
    abandons = (
        db.query(func.count(EventRecord.id))
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "BILLING_QUEUE_ABANDON",
            EventRecord.is_staff.is_(False),
        )
        .scalar()
        or 0
    )
    abandonment_rate = (abandons / joins) if joins else 0.0

    return MetricsResponse(
        store_id=store_id,
        unique_visitors=visitors,
        conversion_rate=round(conversion_rate, 4),
        avg_dwell_per_zone=avg_dwell,
        queue_depth=queue_depth,
        abandonment_rate=round(abandonment_rate, 4),
        computed_at=datetime.now(timezone.utc),
    )
