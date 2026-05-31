from __future__ import annotations

from sqlalchemy.orm import Session

from app.metrics import _mark_conversions
from app.models import EventRecord, SessionRecord
from app.schemas import FunnelResponse, FunnelStage


def compute_funnel(db: Session, store_id: str) -> FunnelResponse:
    _mark_conversions(db, store_id)

    entry_visitors = {
        r.visitor_id
        for r in db.query(EventRecord.visitor_id)
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type.in_(["ENTRY", "REENTRY"]),
            EventRecord.is_staff.is_(False),
        )
        .distinct()
    }

    zone_visitors = {
        r.visitor_id
        for r in db.query(EventRecord.visitor_id)
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]),
            EventRecord.is_staff.is_(False),
            EventRecord.zone_id.isnot(None),
        )
        .distinct()
    }
    zone_visitors &= entry_visitors

    queue_visitors = {
        r.visitor_id
        for r in db.query(EventRecord.visitor_id)
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "BILLING_QUEUE_JOIN",
            EventRecord.is_staff.is_(False),
        )
        .distinct()
    }
    queue_visitors &= zone_visitors

    purchase_visitors = {
        s.visitor_id
        for s in db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.converted.is_(True),
            SessionRecord.is_staff.is_(False),
        )
        .all()
    }
    purchase_visitors &= queue_visitors

    counts = [
        ("Entry", len(entry_visitors)),
        ("Zone Visit", len(zone_visitors)),
        ("Billing Queue", len(queue_visitors)),
        ("Purchase", len(purchase_visitors)),
    ]
    stages: list[FunnelStage] = []
    prev = None
    for name, count in counts:
        dropoff = None
        if prev is not None and prev > 0:
            dropoff = round(100.0 * (1 - count / prev), 2)
        stages.append(FunnelStage(stage=name, count=count, dropoff_pct=dropoff))
        prev = count
    return FunnelResponse(store_id=store_id, stages=stages)
