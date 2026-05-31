from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
DATASET_ROOT = Path(os.getenv("DATASET_ROOT", PROJECT_ROOT / "dataset"))
VIDEO_DIR = Path(os.getenv("VIDEO_DIR", DATASET_ROOT / "videos"))
LAYOUT_PATH = Path(os.getenv("LAYOUT_PATH", DATASET_ROOT / "store_layout.json"))
POS_PATH = Path(os.getenv("POS_PATH", DATASET_ROOT / "pos_transactions.csv"))
EVENTS_OUTPUT = Path(os.getenv("EVENTS_OUTPUT", DATASET_ROOT / "generated_events.jsonl"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(PACKAGE_ROOT / 'data' / 'store_intelligence.db').as_posix()}",
)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8501"))
API_BASE_URL = os.getenv("API_BASE_URL", f"http://localhost:{API_PORT}")

REENTRY_WINDOW_SECONDS = int(os.getenv("REENTRY_WINDOW_SECONDS", "900"))
DWELL_EMIT_INTERVAL_SECONDS = int(os.getenv("DWELL_EMIT_INTERVAL_SECONDS", "30"))
CONVERSION_LOOKBACK_MINUTES = int(os.getenv("CONVERSION_LOOKBACK_MINUTES", "5"))

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
YOLO_CONF = float(os.getenv("YOLO_CONF", "0.35"))
YOLO_IOU = float(os.getenv("YOLO_IOU", "0.5"))
FRAME_STRIDE = int(os.getenv("FRAME_STRIDE", "3"))
MAX_FRAMES_PER_VIDEO = int(os.getenv("MAX_FRAMES_PER_VIDEO", "0"))

PIPELINE_DEVICE = os.getenv("PIPELINE_DEVICE", "cpu")
USE_OSNET = os.getenv("USE_OSNET", "auto").lower()

STAFF_MIN_APPEARANCES = int(os.getenv("STAFF_MIN_APPEARANCES", "3"))
STAFF_MIN_DWELL_SECONDS = int(os.getenv("STAFF_MIN_DWELL_SECONDS", "600"))
STAFF_MIN_ZONES = int(os.getenv("STAFF_MIN_ZONES", "3"))

EVENT_TYPES = {
    "ENTRY",
    "EXIT",
    "REENTRY",
    "ZONE_ENTER",
    "ZONE_EXIT",
    "ZONE_DWELL",
    "BILLING_QUEUE_JOIN",
    "BILLING_QUEUE_ABANDON",
}
