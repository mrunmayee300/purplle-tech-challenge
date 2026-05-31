# Submission Checklist — Purplle Tech Challenge 2026 Round 2

Use this matrix before upload. Run commands from repository **root** unless noted.

---

## Acceptance gate (mandatory)

| # | Requirement | Pass? | How to verify |
|---|-------------|-------|---------------|
| 1 | `docker compose up` no manual steps | ☐ | `docker compose up --build` — wait for healthy API |
| 2 | `/Metrics` returns valid JSON | ☐ | `curl http://localhost:8000/metrics` |
| 3 | Pipeline produces structured events | ☐ | `dataset/generated_events.jsonl` exists |
| 4 | `docs/DESIGN.md` non-trivial | ☐ | ≥1000 words |
| 5 | `docs/CHOICES.md` non-trivial | ☐ | ≥1000 words |
| 6 | System stable (no crash) | ☐ | `pytest` + 5 min API smoke |

**Automated:** `cd store-intelligence && python scripts/verify_evaluation.py`

---

## Detection pipeline (30 marks)

| # | Criteria | Pass? | Evidence |
|---|----------|-------|----------|
| 7 | ENTRY/EXIT events | ☐ | `generated_events.jsonl` |
| 8 | Re-entry handling | ☐ | `REENTRY` type + tests |
| 9 | Staff exclusion | ☐ | `is_staff` + tests |
| 10 | Group entry (N people → N events) | ☐ | test_pipeline |
| 11 | Zone events | ☐ | ZONE_ENTER/EXIT/DWELL |
| 12 | Billing queue events | ☐ | BILLING_QUEUE_* |
| 13 | YOLOv8 + ByteTrack | ☐ | `pipeline/detect.py`, `tracker.py` |

---

## API & business logic (35 marks)

| # | Criteria | Pass? | Evidence |
|---|----------|-------|----------|
| 14 | POST `/events/ingest` | ☐ | Swagger / tests |
| 15 | GET metrics | ☐ | `/metrics` |
| 16 | GET funnel | ☐ | session-based tests |
| 17 | GET heatmap | ☐ | test_heatmap |
| 18 | GET anomalies | ☐ | test_anomalies |
| 19 | GET health | ☐ | test_health |
| 20 | POS conversion (5 min window) | ☐ | metrics.py + test_conversion |
| 21 | No double counting | ☐ | test_funnel |
| 22 | Idempotent ingest | ☐ | test_ingestion |

---

## Production readiness (20 marks)

| # | Criteria | Pass? | Evidence |
|---|----------|-------|----------|
| 23 | Docker Compose | ☐ | `docker-compose.yml` |
| 24 | README setup | ☐ | `README.md` |
| 25 | JSON structured logs | ☐ | `logging_config.py` |
| 26 | Tests ≥70% coverage | ☐ | `pytest` |
| 27 | HTTP 503 on DB down | ☐ | test_health |
| 28 | Dashboard | ☐ | `:8501` |

---

## Engineering thinking (15 marks)

| # | Criteria | Pass? | Evidence |
|---|----------|-------|----------|
| 29 | DESIGN.md architecture | ☐ | `docs/DESIGN.md` |
| 30 | CHOICES.md trade-offs | ☐ | `docs/CHOICES.md` |
| 31 | PROJECT_PLAN.md | ☐ | root |
| 32 | FINAL_REPORT.md | ☐ | root |
| 33 | AI decisions documented | ☐ | DESIGN + CHOICES |

---

## Git / delivery

| # | Criteria | Pass? | Evidence |
|---|----------|-------|----------|
| 34 | `.gitignore` excludes mp4/dataset | ☐ | root `.gitignore` |
| 35 | `docs/DATASET.md` explains data setup | ☐ | present |
| 36 | No secrets in repo | ☐ | manual scan |
| 37 | `assets/` diagrams | ☐ | `assets/*.mmd` |

---

## Pre-upload commands

```bash
cd store-intelligence && pytest
python scripts/verify_evaluation.py
docker compose up --build -d
curl http://localhost:8000/health
```

---

## Delivery package (outside Git)

Zip separately if required:

- `CCTV Footage/*.mp4`
- `dataset/` (or run `prepare_dataset.py` + pipeline)

---

**Last audit:** See `AUDIT_REPORT.md` for score estimate and risks.
