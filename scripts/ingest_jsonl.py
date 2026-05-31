"""Ingest generated_events.jsonl via API (used after pipeline in Docker)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

DATA = Path(__import__("os").environ.get("DATASET_ROOT", Path(__file__).resolve().parents[2] / "dataset"))
API = __import__("os").environ.get("API_BASE_URL", "http://127.0.0.1:8000")
PATH = DATA / "generated_events.jsonl"


def main() -> None:
    if not PATH.exists():
        print(f"No file at {PATH}, skipping ingest")
        return
    events = []
    with PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    if not events:
        return
    for attempt in range(15):
        try:
            with httpx.Client(timeout=120.0) as client:
                for i in range(0, len(events), 100):
                    chunk = events[i : i + 100]
                    r = client.post(f"{API}/events/ingest", json={"events": chunk})
                    r.raise_for_status()
                    print(r.json())
            print(f"Ingested {len(events)} pipeline events")
            return
        except Exception as exc:
            print(f"Waiting for API ({attempt + 1}/15): {exc}")
            time.sleep(2)
    sys.exit(1)


if __name__ == "__main__":
    main()
