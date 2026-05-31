from __future__ import annotations

from app.database import database_available
from app.ingestion import is_feed_stale, last_event_timestamp
from app.schemas import HealthResponse
from sqlalchemy.orm import Session


def health_check(db: Session) -> HealthResponse:
    db_ok = database_available()
    last_ts = last_event_timestamp(db) if db_ok else None
    stale = is_feed_stale(db) if db_ok else True
    status = "healthy" if db_ok and not stale else "degraded"
    if not db_ok:
        status = "unhealthy"
    return HealthResponse(
        status=status,
        last_event_timestamp=last_ts,
        stale_feed=stale,
        database="up" if db_ok else "down",
    )
