from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EventRecord
from app.schemas import HeatmapResponse, HeatmapZone


def compute_heatmap(db: Session, store_id: str) -> HeatmapResponse:
    freq_rows = (
        db.query(EventRecord.zone_id, func.count(EventRecord.id))
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]),
            EventRecord.is_staff.is_(False),
            EventRecord.zone_id.isnot(None),
        )
        .group_by(EventRecord.zone_id)
        .all()
    )
    dwell_rows = (
        db.query(EventRecord.zone_id, func.avg(EventRecord.dwell_ms))
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "ZONE_DWELL",
            EventRecord.is_staff.is_(False),
            EventRecord.zone_id.isnot(None),
        )
        .group_by(EventRecord.zone_id)
        .all()
    )
    dwell_map = {z: (ms or 0) / 1000.0 for z, ms in dwell_rows}
    max_freq = max((c for _, c in freq_rows), default=1) or 1
    total_events = sum(c for _, c in freq_rows)

    zones: list[HeatmapZone] = []
    for zone_id, frequency in freq_rows:
        if not zone_id:
            continue
        avg_dwell = round(dwell_map.get(zone_id, 0.0), 2)
        normalized = round(frequency / max_freq, 4)
        zones.append(
            HeatmapZone(
                zone_id=zone_id,
                frequency=frequency,
                avg_dwell_seconds=avg_dwell,
                normalized_score=normalized,
            )
        )

    confidence = min(1.0, total_events / 50.0) if total_events else 0.0
    return HeatmapResponse(
        store_id=store_id,
        zones=sorted(zones, key=lambda z: z.normalized_score, reverse=True),
        data_confidence=round(confidence, 3),
    )
