#!/usr/bin/env python3
"""Run acceptance-gate checks from the Purplle evaluation framework."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

API = __import__("os").environ.get("API_BASE_URL", "http://localhost:8000")
STORE = "ST1008"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = Path(__import__("os").environ.get("DATASET_ROOT", ROOT.parent / "dataset"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> int:
    all_ok = True

    all_ok &= check("DESIGN.md exists", (DOCS / "DESIGN.md").exists() and (DOCS / "DESIGN.md").stat().st_size > 500)
    all_ok &= check("CHOICES.md exists", (DOCS / "CHOICES.md").exists() and (DOCS / "CHOICES.md").stat().st_size > 500)
    all_ok &= check("store_layout.json", (DATA / "store_layout.json").exists())
    all_ok &= check("pos_transactions.csv", (DATA / "pos_transactions.csv").exists())

    events_file = DATA / "generated_events.jsonl"
    sample_file = DATA / "sample_events.jsonl"
    has_events = events_file.exists() and events_file.stat().st_size > 0
    all_ok &= check(
        "Pipeline events (generated_events.jsonl)",
        has_events or sample_file.exists(),
        str(events_file if has_events else sample_file),
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            health = client.get(f"{API}/health")
            all_ok &= check("GET /health", health.status_code == 200, health.text[:120])

            for path in ("/metrics", "/Metrics", f"/stores/{STORE}/metrics"):
                r = client.get(f"{API}{path}")
                all_ok &= check(f"GET {path}", r.status_code == 200, f"keys={list(r.json().keys())[:5]}")

            funnel = client.get(f"{API}/stores/{STORE}/funnel")
            stages = funnel.json().get("stages", []) if funnel.status_code == 200 else []
            all_ok &= check(
                "GET /funnel",
                funnel.status_code == 200 and len(stages) >= 4,
                f"stages={len(stages)}",
            )

            heatmap = client.get(f"{API}/stores/{STORE}/heatmap")
            all_ok &= check("GET /heatmap", heatmap.status_code == 200)

            anomalies = client.get(f"{API}/stores/{STORE}/anomalies")
            all_ok &= check("GET /anomalies", anomalies.status_code == 200)

            if health.status_code == 200:
                body = health.json()
                all_ok &= check(
                    "Health database up",
                    body.get("database") == "up",
                    json.dumps(body),
                )
    except Exception as exc:
        all_ok = False
        check("API reachable", False, str(exc))

    print("\n" + ("All acceptance checks passed." if all_ok else "Some checks failed."))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
