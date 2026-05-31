from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.config import EVENT_TYPES


class StoreEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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

    @field_validator("event_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        try:
            uuid.UUID(value, version=4)
        except ValueError as exc:
            raise ValueError("event_id must be a valid UUID4") from exc
        return value

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        upper = value.upper()
        if upper not in EVENT_TYPES:
            raise ValueError(f"Unsupported event_type: {value}")
        return upper

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        payload = self.model_dump()
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


def new_event(**kwargs: Any) -> StoreEvent:
    if "event_id" not in kwargs:
        kwargs["event_id"] = str(uuid.uuid4())
    return StoreEvent(**kwargs)
