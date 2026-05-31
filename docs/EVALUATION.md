# Evaluator Quick Start (2-Minute Acceptance Gate)

## Run (zero manual steps)

```bash
# Repository root
docker compose up --build
```

Wait until `store-intelligence-api` is healthy (~45s). Then:

| Check | URL |
|-------|-----|
| Metrics (gate) | http://localhost:8000/metrics |
| Swagger | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |
| Events file | `dataset/generated_events.jsonl` |

## Automated verification

```bash
cd store-intelligence
python scripts/verify_evaluation.py
```

## What happens on startup

1. Postgres starts
2. API container initializes schema
3. `bootstrap_db.py` loads sample + synthetic + pipeline JSONL events
4. Health returns `"status": "healthy"`, `"database": "up"`
5. Dashboard connects to API

## Optional: full CV pipeline on startup

```bash
RUN_PIPELINE_ON_START=1 docker compose up --build
```

Processes CCTV with YOLOv8n + ByteTrack and refreshes `dataset/generated_events.jsonl`.

## Scoring alignment

| Framework area | Implementation |
|----------------|----------------|
| Detection pipeline | `pipeline/` — YOLOv8n, ByteTrack, zones, staff, re-entry |
| API & business logic | `/metrics`, `/funnel`, `/heatmap`, `/anomalies`, POS conversion |
| Production readiness | Docker Compose, JSON logs, pytest ≥70%, health checks |
| Engineering thinking | `docs/DESIGN.md`, `docs/CHOICES.md`, `PROJECT_PLAN.md` |
