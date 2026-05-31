# PROJECT PLAN — Purplle Store Intelligence (Brigade Bangalore)

## 1. Dataset inspection findings

| Asset | Location | Findings |
|-------|----------|----------|
| CCTV | `CCTV Footage/CAM 1-5.mp4` | 1920×1080; CAM 1–3 @ ~29.97fps (~125–149s); CAM 4–5 @ 25fps (~139–146s) |
| POS | `Brigade_Bangalore_*.csv` | 101 line items, 24 unique orders, store `ST1008`, date 10-Apr-2026 |
| Layout XLSX | `Brigade Road - Store layout.xlsx` | Visual floor plan only; strings "Revised"/"Current" — no coordinates |
| Employees in POS | 5 codes | CL2727, CL2063, CL2680, CL1997, CL2541 (staff heuristic context) |

Normalized artifacts: `dataset/store_layout.json`, `dataset/pos_transactions.csv`, `dataset/sample_events.jsonl`.

---

## 2. Video structure

| Camera | File | Role | Zones |
|--------|------|------|-------|
| cam_1 | CAM 1.mp4 | Entry / foyer | entry, foyer |
| cam_2 | CAM 2.mp4 | Makeup aisle | makeup, aisle_north |
| cam_3 | CAM 3.mp4 | Skincare | skincare, personal_care |
| cam_4 | CAM 4.mp4 | Billing | billing, billing_queue |
| cam_5 | CAM 5.mp4 | Exit / trial | trial_room, exit_lane |

Videos are processed independently per camera; visitor continuity across cameras uses Re-ID on **re-entry** (not full multi-camera fusion).

---

## 3. Store layout assumptions

- Polygons defined in **normalized 0–1 image coordinates** per camera.
- Virtual lines at entry camera for ENTRY (downward cross) and EXIT (upward cross).
- Billing queue polygon on cam_4 for queue depth and abandonment.
- Layout file is version-controlled; CAD calibration is future work.

---

## 4. POS correlation strategy

**Rule:** Visitor converted if `ZONE_ENTER` or `ZONE_DWELL` in `billing` / `billing_queue` occurs **≤5 minutes before** POS `timestamp`.

**Data flow:**

1. `scripts/prepare_dataset.py` normalizes raw CSV → `pos_transactions.csv` with ISO timestamps.
2. `compute_metrics()` / `_mark_conversions()` joins sessions to POS at query time.
3. Funnel "Purchase" stage uses `SessionRecord.converted=true`.

**Limitation:** No vision-to-receipt identity—time-window proxy only.

---

## 5. Architecture plan

```
Videos → YOLOv8n → ByteTrack → ZoneMapper + StaffDetector + ReID
    → EventEmitter → EventBus → JSONL + API
    → SQLAlchemy (events, sessions) → FastAPI → Streamlit
```

**Scale path:** SQLite → Postgres → Kafka → Kubernetes (documented in DESIGN.md).

---

## 6. Event generation strategy

| Event | Trigger |
|-------|---------|
| ENTRY | Virtual line cross (entry direction) |
| EXIT | Virtual line cross (exit direction) |
| REENTRY | Re-ID match within window after EXIT |
| ZONE_* | Polygon enter/exit/dwell timer |
| BILLING_QUEUE_JOIN | Enter queue polygon |
| BILLING_QUEUE_ABANDON | Leave billing without POS match |

**Cadence:** `ZONE_DWELL` every 30s while remaining in zone.

**Staff:** `is_staff=true` excludes from visitor analytics.

---

## 7. Edge case handling strategy

| Edge case | Strategy |
|-----------|----------|
| Re-entry | Exited-visitor embedding gallery + time gate |
| Staff | Uniform HSV + long multi-zone presence |
| Group entry | One event per ByteTrack ID |
| Queue abandon | Exit billing zone without conversion flag |
| Camera overlap | Per-camera zones; no duplicate ENTRY for same track |
| Empty store | Zero metrics; heatmap confidence 0 |
| Duplicate API events | Idempotent on `event_id` |
| Partial ingest failure | Per-event status in response |

---

## 8. Testing strategy

| Layer | Tests |
|-------|-------|
| API | test_ingestion, test_metrics, test_funnel, test_anomalies, test_health |
| Edge cases | test_edge_cases |
| Pipeline | test_pipeline, test_process_store_mock |
| Gate | test_evaluation_gate |
| Coverage | pytest-cov ≥70% |

Run: `cd store-intelligence && pytest`

---

## 9. Deployment strategy

**Evaluator path:**

```bash
docker compose up --build
python scripts/verify_evaluation.py
```

**Components:**

- `db`: Postgres 16
- `api`: FastAPI + bootstrap_db on start
- `dashboard`: Streamlit

**Git:** Raw MP4/dataset excluded; see `docs/DATASET.md`.

---

## 10. Event schema mapping

| Field | Source |
|-------|--------|
| event_id | uuid4() |
| store_id | layout (`ST1008`) |
| camera_id | Processing camera |
| visitor_id | ReID engine |
| event_type | State machine |
| timestamp | frame_index/fps + recording_date |
| zone_id | ZoneMapper |
| dwell_ms | Zone timer |
| is_staff | StaffDetector |
| confidence | YOLO score |
| metadata | track_id, queue_depth, etc. |

---

## 11. Deliverables checklist

- [x] `store-intelligence/` application
- [x] `docs/DESIGN.md`, `docs/CHOICES.md`
- [x] `README.md`, `PROJECT_PLAN.md`, `FINAL_REPORT.md`
- [x] `docker-compose.yml` (root + package)
- [x] `tests/` with PROMPT headers
- [x] `assets/` diagrams
- [x] `SUBMISSION_CHECKLIST.md`

---

## 12. Risk register

| Risk | Mitigation |
|------|------------|
| Reviewer missing videos | DATASET.md + prepare script |
| Stale health flag | DEMO_MODE=1 |
| Low pipeline output on quick run | RUN_PIPELINE_ON_START=1 docs |
| Entry count drift | Document line calibration assumption |
