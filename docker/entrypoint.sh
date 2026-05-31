#!/bin/sh
set -e

if [ "$SERVICE" = "dashboard" ]; then
  exec streamlit run dashboard/streamlit_dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
fi

if [ "$SERVICE" = "pipeline" ]; then
  exec python pipeline/run_pipeline.py "$@"
fi

echo "Initializing database..."
python -c "from app.database import init_db; init_db(); print('Database ready')"

if [ "${BOOTSTRAP_ON_START:-1}" = "1" ]; then
  echo "Bootstrapping events..."
  python scripts/bootstrap_db.py
fi

if [ "${RUN_PIPELINE_ON_START:-0}" = "1" ]; then
  echo "Running CV pipeline (may take several minutes)..."
  python pipeline/run_pipeline.py --no-api || echo "Pipeline finished with warnings"
  python scripts/bootstrap_db.py || true
fi

echo "Starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
