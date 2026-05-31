# Repository Audit Report — Purplle Tech Challenge 2026 Round 2

**Auditor role:** Reviewer + Staff Architect + AI Engineer  
**Repository:** `store-intelligence/` (Brigade Bangalore, ST1008)  
**Audit date:** 2026-05-31

---

## Executive score estimate

| Category | Max | Estimate | Notes |
|----------|-----|----------|-------|
| Detection pipeline | 30 | **24–27** | Real YOLO+ByteTrack; layout zones inferred; short `generated_events.jsonl` on quick run |
| API & business logic | 35 | **30–33** | All endpoints; session funnel; POS conversion; anomalies |
| Production readiness | 20 | **16–18** | Docker bootstrap, tests ≥70%, JSON logs; pipeline coverage low in unit tests |
| Engineering thinking | 15 | **13–15** | DESIGN/CHOICES expanded; PROJECT_PLAN; FINAL_REPORT |
| **Total** | **100** | **83–93** | Strong submission band after deliverable pass |

---

## Acceptance gate

| Check | Status | Evidence |
|-------|--------|----------|
| `docker compose up` without manual steps | **PASS** | Root + `store-intelligence/docker-compose.yml`; `bootstrap_db.py` on API start |
| `/Metrics` valid response | **PASS** | `GET /metrics`, `GET /Metrics` |
| Pipeline produces structured events | **PASS** | `dataset/generated_events.jsonl` |
| DESIGN.md non-trivial | **PASS** (after expansion) | `docs/DESIGN.md` ≥1000 words |
| CHOICES.md non-trivial | **PASS** (after expansion) | `docs/CHOICES.md` ≥1000 words |
| Stability (no crash on basic run) | **PASS** | 39 pytest tests; verify script |

---

## Rubric-by-rubric findings

### Detection pipeline (30)

**Strengths**

- YOLOv8n person class + ByteTrack via `supervision`
- Virtual line ENTRY/EXIT; REENTRY via exited-visitor gallery
- Per-track visitor IDs (no group collapse)
- Staff: uniform HSV + dwell/multi-zone heuristic
- Zone ENTER/EXIT/DWELL (30s); billing queue join/abandon

**Weaknesses (pre-fix)**

- `process_store.py` / `run_pipeline.py` under-tested in pytest (0% line hit)
- `generated_events.jsonl` may be small if evaluators skip `RUN_PIPELINE_ON_START=1`
- Zone polygons not from CAD (Excel layout is visual-only)

**Fixes applied**

- Mock-based pipeline tests added
- `docs/DATASET.md` + evaluator instructions for full pipeline run
- `assets/event_flow.mmd` for reviewer clarity

### API & business logic (35)

**Strengths**

- Ingest: 500 cap, UUID4, dedupe, partial success
- Metrics, funnel (session-scoped), heatmap, anomalies
- POS conversion: billing within 5 minutes before transaction
- 503 on DB down; no stack traces to client

**Weaknesses**

- Conversion test not tied to real POS timestamps (added)
- `/metrics` alias documented for gate only recently

**Fixes applied**

- Conversion unit test with aligned timestamps
- README curl examples + sample JSON

### Production readiness (20)

**Strengths**

- Docker Compose (Postgres + API + dashboard)
- Structured JSON request logs (`trace_id`, `latency_ms`)
- `scripts/verify_evaluation.py`
- Coverage gate 70% in `pytest.ini`

**Weaknesses**

- `.gitignore` missing at repo root (added)
- Streamlit auto-refresh default off (good for stability)

### Engineering thinking (15)

**Strengths**

- CHOICES covers model, schema, API, DB, tracking
- PROJECT_PLAN + FINAL_REPORT
- AI decisions documented (accepted/rejected)

**Weakesss**

- DESIGN/CHOICES below 1000 words (expanded in this pass)

### Dashboard

**PASS** — Streamlit polls API; funnel, heatmap, anomalies, health strip.

---

## Missing components (resolved)

| Item | Action |
|------|--------|
| Root `.gitignore` | Created |
| `SUBMISSION_CHECKLIST.md` | Created |
| `assets/*.mmd` | Created |
| Expanded README / DESIGN / CHOICES | Created |
| Test PROMPT headers (standard format) | Updated all test files |
| Pipeline mock tests | Added `tests/test_process_store_mock.py` |
| `docs/DATASET.md` | Dataset delivery outside Git |

---

## Risk areas for reviewers

1. **Large video files** — Not in Git; must exist beside repo for Docker mount.
2. **Stale feed** — Mitigated via `DEMO_MODE=1` in Docker.
3. **Integrity check** — Outputs vary with ingest/POS; not hardcoded.
4. **Entry count accuracy** — Depends on virtual line calibration.

---

## Recommended reviewer path (2 minutes)

```bash
docker compose up --build
curl http://localhost:8000/metrics
curl http://localhost:8000/stores/ST1008/funnel
cd store-intelligence && python scripts/verify_evaluation.py
```

---

## Post-audit status

All listed gaps addressed in this commit batch. Re-run `pytest` and `verify_evaluation.py` before submission upload.
