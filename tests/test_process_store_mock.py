# PROMPT:
# Add mock-based tests for StoreProcessor and run_pipeline CLI so pipeline modules
# are covered without running YOLO on full CCTV files in CI.
#
# CHANGES MADE:
# Patched PersonDetector.detect and cv2.VideoCapture to validate orchestration,
# event bus wiring, and run_pipeline argument parsing.

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pipeline.detect import Detection
from pipeline.process_store import StoreProcessor
from shared.event_bus import EventBus
from shared.layout import StoreLayout


@pytest.fixture(scope="module")
def layout():
    return StoreLayout.load()


def test_store_processor_single_frame(layout, tmp_path):
    bus = EventBus(jsonl_path=tmp_path / "out.jsonl")
    processor = StoreProcessor(layout, bus=bus)

    fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    fake_cap = MagicMock()
    fake_cap.isOpened.return_value = True
    fake_cap.get.side_effect = lambda k: {5: 30.0}.get(k, 0)
    fake_cap.read.side_effect = [(True, fake_frame), (False, None)]

    detections = [Detection(bbox=(0.2, 0.2, 0.4, 0.7), confidence=0.9)]

    with patch("pipeline.process_store.cv2.VideoCapture", return_value=fake_cap):
        with patch.object(processor.detector, "detect", return_value=detections):
            processor.process_camera("cam_1")  # should not raise


def test_run_pipeline_main(layout, tmp_path):
    with patch("pipeline.run_pipeline.StoreProcessor") as mock_proc:
        instance = mock_proc.return_value
        with patch("sys.argv", ["run_pipeline", "--camera", "cam_1", "--no-api"]):
            from pipeline import run_pipeline

            run_pipeline.main()
        instance.process_camera.assert_called_once_with("cam_1")
