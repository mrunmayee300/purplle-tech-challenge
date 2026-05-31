from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: str | None = None
    dwell_ms: int | None = None
    is_staff: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    events: list[EventIn] = Field(max_length=500)


class IngestResultItem(BaseModel):
    event_id: str
    status: str
    error: str | None = None


class IngestResponse(BaseModel):
    accepted: int
    duplicate: int
    failed: int
    results: list[IngestResultItem]


class MetricsResponse(BaseModel):
    store_id: str
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone: dict[str, float]
    queue_depth: int
    abandonment_rate: float
    computed_at: datetime


class FunnelStage(BaseModel):
    stage: str
    count: int
    dropoff_pct: float | None = None


class FunnelResponse(BaseModel):
    store_id: str
    stages: list[FunnelStage]


class HeatmapZone(BaseModel):
    zone_id: str
    frequency: int
    avg_dwell_seconds: float
    normalized_score: float


class HeatmapResponse(BaseModel):
    store_id: str
    zones: list[HeatmapZone]
    data_confidence: float


class AnomalyItem(BaseModel):
    anomaly_type: str
    severity: str
    message: str
    suggested_action: str
    detected_at: datetime


class AnomaliesResponse(BaseModel):
    store_id: str
    anomalies: list[AnomalyItem]


class HealthResponse(BaseModel):
    status: str
    last_event_timestamp: datetime | None
    stale_feed: bool
    database: str
