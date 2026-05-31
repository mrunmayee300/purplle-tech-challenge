# Engineering Choices — Store Intelligence Platform

This document records **major architectural decisions** for the Purplle Tech Challenge 2026 Round 2 submission. Each section follows: options considered → AI recommendation → evaluation → tradeoffs → **final choice**.

---

## Decision 1: Detection model selection

### Options considered

| Model | Params | Speed (CPU) | Person mAP (COCO) |
|-------|--------|-------------|-------------------|
| YOLOv8n | ~3M | Fastest | Good |
| YOLOv8s | ~11M | Medium | Better |
| YOLOv9 | Varies | Slower | Incremental |
| RT-DETR | Transformer | Slow | Strong |
| MediaPipe | Lightweight | Very fast | Pose not full bbox |

### AI recommendation

Cursor/AI assistants typically suggest **YOLOv8n or YOLOv8s** for edge retail CCTV on CPU, with **ByteTrack** downstream. RT-DETR is recommended only when GPU inference is guaranteed.

### Evaluation

- Brigade videos: 1920×1080, ~25–30 FPS, moderate crowd density.
- Evaluators run Docker on laptops—GPU not assumed.
- Challenge rubric weights **working system** over SOTA mAP.

### Tradeoffs

| Choice | Pros | Cons |
|--------|------|------|
| YOLOv8n | Fast, one-line Ultralytics API | More false positives in clutter |
| YOLOv8s | +2–4 mAP | 3× slower on CPU |
| RT-DETR | Accuracy | Heavy deps, latency |
| MediaPipe | Speed | Not full person boxes for overlap counting |

### Final choice: **YOLOv8n**

Configurable via `YOLO_MODEL` env. Acceptable error margin on entry counts when paired with line-crossing logic (temporal constraint reduces single-frame noise).

---

## Decision 2: Event schema design

### Why event-driven architecture?

Retail analytics naturally decompose into **facts** (“visitor X entered zone Y at time T”). Events provide:

1. **Auditability** — replay JSONL to debug disputes.
2. **Decoupling** — CV team ships events; API team ingests without redeploying models.
3. **Extensibility** — new event types without schema migrations for every metric.

### Alternatives

| Approach | Description | Verdict |
|----------|-------------|---------|
| Direct DB writes from pipeline | Skip event envelope | Rejected — tight coupling |
| Batch CSV hourly | Simple | Rejected — no real-time path |
| Stream processing (Flink) | Scalable | Future — overkill for R2 |
| **Canonical events + ingest API** | Selected | Best balance |

### Schema shape

Flat JSON with required fields (not CloudEvents) for direct SQL mapping:

```
event_id, store_id, camera_id, visitor_id, event_type,
timestamp, zone_id, dwell_ms, is_staff, confidence, metadata
```

### Scalability

- Kafka topic `store.{store_id}.events` with JSON value.
- Consumers idempotent on `event_id`.

### Observability

- JSONL mirror on disk for offline inspection (reviewer-friendly).
- Metadata bag holds `track_id`, `queue_depth` without schema churn.

### Debugging

Invalid events fail validation with per-event errors in ingest response (`accepted`, `duplicate`, `failed` arrays).

### Final choice: **Validated flat event schema + event bus**

---

## Decision 3: API architecture choice

### Options

| Framework | Validation | Async | OpenAPI | Performance |
|-----------|------------|-------|---------|-------------|
| **FastAPI** | Pydantic native | Yes | Auto | High (Starlette) |
| Flask | Manual/marshmallow | Sync default | Plugin | Medium |
| Express | Joi/Zod | Yes | Manual | High |
| Go Fiber | Struct tags | Yes | Manual | Very high |

### AI recommendation

FastAPI is the default AI coding assistant suggestion for Python microservices with typed request bodies—matches ingest batch validation requirement.

### Evaluation

- Need `POST /events/ingest` with 500-item payload validation.
- Need multiple read endpoints with shared DB session.
- Evaluators benefit from `/docs` Swagger UI.

### Tradeoffs

FastAPI adds stack complexity vs Flask but eliminates boilerplate for schemas and error responses.

### Final choice: **FastAPI monolith**

Single deployable unit: ingestion + analytics + health. Microservices deferred until Kafka migration.

---

## Decision 4: Database choice

### SQLite vs PostgreSQL

| | SQLite | PostgreSQL |
|---|--------|------------|
| Setup | Zero config | Docker service |
| Concurrency | Single writer | Multi-client |
| Challenge local dev | Ideal | Heavier |
| Production 40 stores | Insufficient | Appropriate |

### Why SQLite now

- Developers run `uvicorn` without Docker.
- Unit tests use in-memory/file SQLite.

### Why PostgreSQL in Docker

- `docker-compose.yml` matches production readiness rubric.
- Same SQLAlchemy models—no code fork.

### Future

- Read replicas for dashboard queries.
- Partition `events` by `store_id` + month.

### Final choice: **SQLite local, PostgreSQL in Compose**

---

## Decision 5: Tracking and Re-ID strategy

### Trackers compared

| Tracker | Mechanism | Pros | Cons |
|---------|-----------|------|------|
| **ByteTrack** | High/low conf association | Fast, simple | Camera-local only |
| DeepSORT | CNN embedding + Kalman | Classic | Heavier, tuning |
| StrongSORT | Improved DeepSORT | Accuracy | Dependencies |

### AI recommendation

Use **ByteTrack** with YOLO—standard Ultralytics ecosystem path.

### Re-ID strategy

**Problem:** Track IDs reset per camera; business needs visitor continuity on **re-entry after exit**.

**Approach:**

1. On EXIT, move embedding to exited gallery with timestamp.
2. On new track, match exited gallery within `reentry_window_seconds` (default 900s).
3. OSNet if `torchreid` weights available; else HSV histogram + aspect ratio.

**Explicitly NOT matching active tracks across different people** — prevents group collapse bug.

### Group entry requirement

Three people entering together → three `ENTRY` events because three ByteTrack IDs fire three line crossings → three `visitor_id` assignments.

### Final choice: **ByteTrack + exited-gallery Re-ID**

---

## Decision 6: Staff detection

No labeled staff dataset.

**AI suggestion:** Train uniform classifier (needs labels).

**Final:** HSV uniform bands (Purplle purple/black) + recurrence heuristic (appearances ≥3, dwell ≥600s, zones ≥3).

Staff events still emitted (`is_staff=true`) for audit but filtered from KPI queries.

---

## Decision 7: Conversion attribution

**Business rule:** Shopper converted if present in billing zone within **5 minutes before** POS timestamp.

**AI alternative:** Match on phone number from POS—rejected (no vision-to-POS identity link in dataset).

**Implementation:** Query-time join in `compute_metrics()` reading `pos_transactions.csv`.

---

## Decision 8: Anomaly detection

**AI suggestion:** Train autoencoder on zone counts.

**Final:** Interpretable thresholds (QUEUE_SPIKE, CONVERSION_DROP, DEAD_ZONE) with `suggested_action` strings—reviewers can reason about alerts in 2-minute eval window.

---

## Decision 9: Dashboard technology

Streamlit chosen for **speed of delivery** and Python-only stack. Tradeoff: not production-grade for 1000 concurrent users—acceptable for challenge; React migration documented.

---

## Decision 10: Git and dataset handling

**AI suggestion:** Commit everything including MP4.

**Final:** `.gitignore` excludes `dataset/`, `CCTV Footage/`, videos—deliver separately. `docs/DATASET.md` explains layout. Prevents GitHub LFS failures and matches integrity expectations (system reads real files locally).

---

## Summary table

| # | Topic | Final choice |
|---|-------|--------------|
| 1 | Detection | YOLOv8n |
| 2 | Schema | Flat validated events + bus |
| 3 | API | FastAPI |
| 4 | Database | SQLite / PostgreSQL |
| 5 | Tracking | ByteTrack + Re-ID gallery |
| 6 | Staff | Heuristics |
| 7 | Conversion | POS time window |
| 8 | Anomalies | Rule-based |
| 9 | Dashboard | Streamlit |
| 10 | Git | Exclude raw dataset |

---

## AI suggestions rejected (with reasons)

1. **Hardcoded API responses** — fails integrity check; all metrics derived from DB.
2. **Single visitor counter** — violates group entry requirement.
3. **CloudEvents wrapper** — unnecessary nesting for SQL store.
4. **Immediate Kafka requirement** — operational burden for reviewers.
5. **YOLOv8s default** — risk of timeout on CPU-only evaluation machines.

This CHOICES document should be read alongside `docs/DESIGN.md` and `AUDIT_REPORT.md` for full submission context.
