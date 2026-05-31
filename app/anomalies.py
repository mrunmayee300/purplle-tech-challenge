from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.metrics import compute_metrics
from app.models import EventRecord
from app.schemas import AnomaliesResponse, AnomalyItem


def detect_anomalies(db: Session, store_id: str) -> AnomaliesResponse:
    now = datetime.now(timezone.utc)
    anomalies: list[AnomalyItem] = []
    metrics = compute_metrics(db, store_id)

    hour_ago = now - timedelta(hours=1)
    recent_joins = (
        db.query(func.count(EventRecord.id))
        .filter(
            EventRecord.store_id == store_id,
            EventRecord.event_type == "BILLING_QUEUE_JOIN",
            EventRecord.timestamp >= hour_ago,
        )
        .scalar()
        or 0
    )
    if metrics.queue_depth >= 5 or recent_joins >= 8:
        anomalies.append(
            AnomalyItem(
                anomaly_type="QUEUE_SPIKE",
                severity="high" if metrics.queue_depth >= 7 else "medium",
                message=f"Billing queue depth elevated ({metrics.queue_depth})",
                suggested_action="Open additional billing counter or deploy floor staff to queue",
                detected_at=now,
            )
        )

    if metrics.conversion_rate < 0.05 and metrics.unique_visitors >= 5:
        anomalies.append(
            AnomalyItem(
                anomaly_type="CONVERSION_DROP",
                severity="high",
                message=f"Conversion rate dropped to {metrics.conversion_rate:.1%}",
                suggested_action="Review billing wait times and in-store promotions near checkout",
                detected_at=now,
            )
        )

    zone_counts = (
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
    if zone_counts:
        frequencies = {z: c for z, c in zone_counts}
        avg_freq = sum(frequencies.values()) / len(frequencies)
        for zone_id, count in frequencies.items():
            if count < avg_freq * 0.2 and avg_freq >= 3:
                anomalies.append(
                    AnomalyItem(
                        anomaly_type="DEAD_ZONE",
                        severity="medium",
                        message=f"Zone '{zone_id}' has unusually low traffic ({count} events)",
                        suggested_action="Reallocate signage or staff to activate underperforming zone",
                        detected_at=now,
                    )
                )
                break

    return AnomaliesResponse(store_id=store_id, anomalies=anomalies)
