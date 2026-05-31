from __future__ import annotations

import uuid
from datetime import datetime, timezone


def make_event(**kwargs):
    base = {
        "event_id": str(uuid.uuid4()),
        "store_id": "ST1008",
        "camera_id": "cam_1",
        "visitor_id": "v-test",
        "event_type": "ENTRY",
        "timestamp": datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        "zone_id": "entry",
        "dwell_ms": None,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {},
    }
    base.update(kwargs)
    return base
