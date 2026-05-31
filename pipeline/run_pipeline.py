#!/usr/bin/env python3
"""CLI entrypoint for store video processing pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.process_store import StoreProcessor
from shared.config import EVENTS_OUTPUT, VIDEO_DIR
from shared.event_bus import EventBus
from shared.layout import StoreLayout

logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","message":"%(message)s","logger":"%(name)s"}',
)
logger = logging.getLogger("run_pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run store intelligence CV pipeline")
    parser.add_argument("--camera", help="Process single camera id", default=None)
    parser.add_argument("--layout", type=Path, default=None)
    parser.add_argument("--video-dir", type=Path, default=VIDEO_DIR)
    parser.add_argument("--output", type=Path, default=EVENTS_OUTPUT)
    parser.add_argument("--no-api", action="store_true")
    args = parser.parse_args()

    layout = StoreLayout.load(args.layout)
    if args.output.exists():
        args.output.unlink()
    bus = EventBus(jsonl_path=args.output, api_url=None if args.no_api else None)
    processor = StoreProcessor(layout, video_root=args.video_dir, bus=bus)

    if args.camera:
        processor.process_camera(args.camera)
    else:
        processor.process_all_cameras()

    logger.info("Pipeline complete. Events written to %s", args.output)


if __name__ == "__main__":
    main()
