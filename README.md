# Store Intelligence System

**Purplle Tech Challenge 2026 — Round 2**  
Brigade Bangalore (`ST1008`) | Computer vision → business analytics

---

## Project overview

The **Store Intelligence System** transforms raw in-store CCTV footage and POS transactions into **actionable retail metrics**: unique visitors, conversion rate, zone heatmaps, billing queue depth, abandonment rate, and operational anomalies.

### Purpose

Retail leaders need to understand **how shoppers move** and **where revenue is lost**—not just raw footfall. This platform:

1. Detects and tracks people across five camera views.
2. Emits a canonical **event stream** (entry, zones, billing queue, staff flags).
3. Ingests events into a database with session semantics.
4. Exposes REST APIs and a live dashboard aligned with store KPIs.

### Architecture overview

```
CCTV (5 cams) → YOLOv8n → ByteTrack → Zones / Staff / Re-ID → Events
                                                      ↓
                              JSONL + POST /events/ingest → PostgreSQL
                                                      ↓
                         FastAPI (metrics, funnel, heatmap, anomalies)
                                                      ↓
                                    Streamlit dashboard
```

See `docs/DESIGN.md` for full architecture and `assets/architecture.mmd` for diagrams.

### Features

| Area | Capability |
|------|------------|
| Detection | YOLOv8n (COCO person class) |
| Tracking | ByteTrack persistent `track_id` |
| Traffic | Virtual line ENTRY / EXIT / REENTRY |
| Zones | ZONE_ENTER, ZONE_EXIT, ZONE_DWELL (30s) |
| Billing | BILLING_QUEUE_JOIN, BILLING_QUEUE_ABANDON |
| Staff | Uniform color + recurrence heuristic; excluded from KPIs |
| Re-ID | OSNet optional; appearance + time window fallback |
| API | Ingest (500/batch), metrics, funnel, heatmap, anomalies, health |
| Ops | Docker Compose, JSON logs, pytest ≥70% coverage |

---

## Repository structure

```
purplle/                          # Submission root
├── docker-compose.yml            # Start full stack from root
├── CCTV Footage/                 # Raw MP4 (not in Git — see docs/DATASET.md)
├── dataset/                      # Normalized data (not in Git)
├── scripts/prepare_dataset.py
└── store-intelligence/
    ├── pipeline/                 # CV + event generation
    ├── app/                      # FastAPI + SQLAlchemy
    ├── dashboard/                # Streamlit UI
    ├── shared/                   # Config, schema, event bus, layout
    ├── tests/                    # Pytest suite
    ├── scripts/                  # bootstrap, verify, seed
    ├── docs/                     # DESIGN, CHOICES, EVALUATION, DATASET
    ├── assets/                   # Mermaid diagrams
    ├── README.md                 # This file
    ├── PROJECT_PLAN.md
    ├── FINAL_REPORT.md
    ├── AUDIT_REPORT.md
    └── SUBMISSION_CHECKLIST.md
```

---

## Installation

### Prerequisites

- Docker Desktop (recommended), **or** Python 3.11+
- Challenge dataset on disk (see `docs/DATASET.md`)

### Clone and prepare

```bash
git clone <your-repo-url>
cd purplle
python scripts/prepare_dataset.py
```

Place `CCTV Footage/CAM 1.mp4` … `CAM 5.mp4` next to `dataset/` per `docs/DATASET.md`.

### Docker (recommended for evaluators)

```bash
# From repository root
docker compose up --build
```

| Service | URL |
|---------|-----|
| API Swagger | http://localhost:8000/docs |
| Metrics gate | http://localhost:8000/metrics |
| Dashboard | http://localhost:8501 |

Verify acceptance gate:

```bash
cd store-intelligence
python scripts/verify_evaluation.py
```

Optional full CV run on container start:

```bash
RUN_PIPELINE_ON_START=1 docker compose up --build
```

### Local Python

```bash
cd store-intelligence
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=sqlite:///./data/store_intelligence.db
export DATASET_ROOT=../dataset
export DEMO_MODE=1
python scripts/bootstrap_db.py
uvicorn app.main:app --reload --port 8000
```

---

## Running detection pipeline

```bash
cd store-intelligence
export VIDEO_DIR=../CCTV\ Footage
export DATASET_ROOT=../dataset
export FRAME_STRIDE=5
export MAX_FRAMES_PER_VIDEO=120   # increase for full video
python pipeline/run_pipeline.py
```

**Outputs:**

| Output | Location |
|--------|----------|
| Event JSONL | `dataset/generated_events.jsonl` |
| Optional API push | Set `API_BASE_URL` and omit `--no-api` |

Each line is a validated event:

```json
{
  "event_id": "uuid4",
  "store_id": "ST1008",
  "camera_id": "cam_1",
  "visitor_id": "v-0001",
  "event_type": "ZONE_ENTER",
  "timestamp": "2026-04-10T12:00:00+00:00",
  "zone_id": "foyer",
  "dwell_ms": null,
  "is_staff": false,
  "confidence": 0.91,
  "metadata": {"track_id": 1}
}
```

Single camera:

```bash
python pipeline/run_pipeline.py --camera cam_1 --no-api
```

---

## Running dashboard

```bash
export API_BASE_URL=http://localhost:8000
export STORE_ID=ST1008
streamlit run dashboard/streamlit_dashboard.py
```

Open http://localhost:8501 — enable **Auto-refresh** in the sidebar if desired.

---

## API endpoints

Base URL: `http://localhost:8000`

### POST `/events/ingest`

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "store_id": "ST1008",
      "camera_id": "cam_1",
      "visitor_id": "v-demo-01",
      "event_type": "ENTRY",
      "timestamp": "2026-04-10T12:15:10+00:00",
      "zone_id": "entry",
      "dwell_ms": null,
      "is_staff": false,
      "confidence": 0.92,
      "metadata": {}
    }]
  }'
```

### GET `/stores/{id}/metrics` and `/metrics`

```bash
curl http://localhost:8000/metrics
curl http://localhost:8000/stores/ST1008/metrics
```

### GET `/stores/{id}/funnel`

```bash
curl http://localhost:8000/stores/ST1008/funnel
```

### GET `/stores/{id}/heatmap`

```bash
curl http://localhost:8000/stores/ST1008/heatmap
```

### GET `/stores/{id}/anomalies`

```bash
curl http://localhost:8000/stores/ST1008/anomalies
```

### GET `/health`

```bash
curl http://localhost:8000/health
```

---

## Sample responses

### Metrics

```json
{
  "store_id": "ST1008",
  "unique_visitors": 4,
  "conversion_rate": 0.25,
  "avg_dwell_per_zone": {"makeup": 45.0, "billing": 120.0},
  "queue_depth": 2,
  "abandonment_rate": 0.2,
  "computed_at": "2026-04-10T19:00:00+00:00"
}
```

### Funnel

```json
{
  "store_id": "ST1008",
  "stages": [
    {"stage": "Entry", "count": 10, "dropoff_pct": null},
    {"stage": "Zone Visit", "count": 8, "dropoff_pct": 20.0},
    {"stage": "Billing Queue", "count": 4, "dropoff_pct": 50.0},
    {"stage": "Purchase", "count": 2, "dropoff_pct": 50.0}
  ]
}
```

### Heatmap

```json
{
  "store_id": "ST1008",
  "zones": [
    {
      "zone_id": "makeup",
      "frequency": 42,
      "avg_dwell_seconds": 38.5,
      "normalized_score": 1.0
    }
  ],
  "data_confidence": 0.84
}
```

### Anomalies

```json
{
  "store_id": "ST1008",
  "anomalies": [
    {
      "anomaly_type": "QUEUE_SPIKE",
      "severity": "high",
      "message": "Billing queue depth elevated (6)",
      "suggested_action": "Open additional billing counter or deploy floor staff to queue",
      "detected_at": "2026-04-10T19:00:00+00:00"
    }
  ]
}
```

### Health

```json
{
  "status": "healthy",
  "last_event_timestamp": "2026-04-10T16:55:00+00:00",
  "stale_feed": false,
  "database": "up"
}
```

---

## Edge cases handled

| Case | Behavior |
|------|----------|
| **Re-entry** | `REENTRY` if same visitor exits and returns within configurable window |
| **Staff movement** | `is_staff=true`; excluded from visitor metrics and funnel |
| **Group entry** | One `ENTRY` per track ID — never merged into one visitor |
| **Queue abandonment** | `BILLING_QUEUE_ABANDON` without POS correlation |
| **Camera overlap** | Per-camera zones; visitor_id linked via Re-ID on re-entry |
| **Empty store** | Metrics return zeros; funnel empty; heatmap `data_confidence=0` |
| **Duplicate ingest** | Idempotent on `event_id` |
| **DB unavailable** | HTTP 503 structured JSON, no stack trace |

---

## Testing

```bash
cd store-intelligence
pytest
```

Coverage threshold: **70%** (`pytest.ini`).

---

## Documentation index

| Document | Description |
|----------|-------------|
| `docs/DESIGN.md` | System design (1000+ words) |
| `docs/CHOICES.md` | Engineering decisions (1000+ words) |
| `PROJECT_PLAN.md` | Plan and assumptions |
| `FINAL_REPORT.md` | Submission report |
| `AUDIT_REPORT.md` | Rubric audit |
| `SUBMISSION_CHECKLIST.md` | Pass/fail matrix |
| `docs/EVALUATION.md` | 2-minute reviewer guide |

---

## Future improvements

- CAD-calibrated zone polygons and line crossing
- Cross-camera global identity graph
- Kafka ingest + Flink aggregations for 40×3 cameras
- GPU Kubernetes pipeline workers
- React dashboard with WebSocket live events
- Model monitoring and drift detection

---

## License & attribution

Built for Purplle Tech Challenge 2026 Round 2. Dataset provided by Purplle; implementation is original work with documented AI-assisted design decisions in `docs/CHOICES.md`.
