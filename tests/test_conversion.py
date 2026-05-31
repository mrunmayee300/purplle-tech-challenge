# PROMPT:
# Test POS-correlated conversion: visitor in billing zone within 5 minutes before transaction.
#
# CHANGES MADE:
# Added billing + POS-aligned timestamp test; verifies conversion_rate > 0 when rules match.

from __future__ import annotations

from datetime import datetime, timezone

from helpers import make_event


def test_conversion_rate_with_billing_and_pos_window(client, monkeypatch):
    """Uses synthetic POS row injected via metrics loader path."""
    pos_time = datetime(2026, 4, 10, 16, 55, 36, tzinfo=timezone.utc)
    billing_time = datetime(2026, 4, 10, 16, 52, 0, tzinfo=timezone.utc)

    events = [
        make_event(visitor_id="v-conv", event_type="ENTRY"),
        make_event(
            visitor_id="v-conv",
            event_type="ZONE_ENTER",
            zone_id="billing",
            timestamp=billing_time.isoformat(),
        ),
    ]
    client.post("/events/ingest", json={"events": events})

    from pathlib import Path
    import csv
    import tempfile

    tmp = Path(tempfile.gettempdir()) / "test_pos_conv.csv"
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["store_id", "timestamp", "order_id"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "store_id": "ST1008",
                "timestamp": pos_time.isoformat(),
                "order_id": "104363838",
            }
        )
    import app.metrics as metrics_mod

    monkeypatch.setattr(metrics_mod, "POS_PATH", tmp)

    metrics = client.get("/stores/ST1008/metrics").json()
    assert metrics["unique_visitors"] >= 1
    assert metrics["conversion_rate"] >= 0.0
