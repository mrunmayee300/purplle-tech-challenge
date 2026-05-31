from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np

from pipeline.detect import PersonDetector
from pipeline.event_emitter import EventEmitter
from pipeline.reid import ReIdentificationEngine
from pipeline.staff_detector import StaffDetector
from pipeline.tracker import ByteTrackerWrapper, TrackState
from pipeline.zone_mapper import ZoneMapper
from shared.config import (
    DWELL_EMIT_INTERVAL_SECONDS,
    EVENTS_OUTPUT,
    FRAME_STRIDE,
    MAX_FRAMES_PER_VIDEO,
    REENTRY_WINDOW_SECONDS,
    VIDEO_DIR,
)
from shared.event_bus import EventBus
from shared.layout import StoreLayout

logger = logging.getLogger(__name__)


class StoreProcessor:
    def __init__(
        self,
        layout: StoreLayout,
        video_root: Path | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.layout = layout
        self.video_root = video_root or VIDEO_DIR
        self.bus = bus or EventBus(jsonl_path=EVENTS_OUTPUT)
        self.detector = PersonDetector()
        self.reid = ReIdentificationEngine(
            reentry_window_seconds=REENTRY_WINDOW_SECONDS
        )
        self.staff_detector = StaffDetector(layout)
        self.zone_mapper = ZoneMapper(layout)
        self.track_to_visitor: dict[int, str] = {}
        self.track_history: dict[int, list[tuple[float, float]]] = {}
        self.track_prev_centroid: dict[int, tuple[float, float] | None] = {}
        self.staff_tracks: set[int] = set()

    def process_camera(self, camera_id: str) -> list:
        video_path = self.layout.video_path(camera_id, self.video_root)
        if not video_path.exists():
            alt = self.video_root.parent / "CCTV Footage" / self.layout.cameras[camera_id]["video_file"]
            video_path = alt if alt.exists() else video_path
        logger.info("Processing %s from %s", camera_id, video_path)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        store_id = self.layout.store_id
        tracker = ByteTrackerWrapper()
        emitter = EventEmitter(self.layout, self.bus, store_id, camera_id)
        events_emitted = []
        frame_idx = 0
        processed = 0
        recording_date = self.layout.data.get("recording_date", "2026-04-10")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % FRAME_STRIDE != 0:
                frame_idx += 1
                continue
            if MAX_FRAMES_PER_VIDEO and processed >= MAX_FRAMES_PER_VIDEO:
                break

            h, w = frame.shape[:2]
            timestamp = _frame_timestamp(recording_date, frame_idx, fps)
            dt = FRAME_STRIDE / fps

            detections = self.detector.detect(frame)
            tracks = tracker.update(detections, (h, w))

            for track in tracks:
                events_emitted.extend(
                    self._process_track(
                        track, frame, emitter, camera_id, timestamp, dt
                    )
                )
            processed += 1
            frame_idx += FRAME_STRIDE

        cap.release()
        self.staff_tracks |= self.staff_detector.finalize()
        return events_emitted

    def _process_track(
        self,
        track: TrackState,
        frame: np.ndarray,
        emitter: EventEmitter,
        camera_id: str,
        timestamp: datetime,
        dt: float,
    ) -> list:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = track.bbox
        crop = frame[
            max(0, int(y1 * h)) : min(h, int(y2 * h)),
            max(0, int(x1 * w)) : min(w, int(x2 * w)),
        ]
        centroid = track.centroid
        history = self.track_history.setdefault(track.track_id, [])
        history.append(centroid)
        if len(history) > 30:
            history.pop(0)

        is_staff = self.staff_detector.observe(
            track.track_id, crop, self.zone_mapper.zone_at_point(camera_id, centroid), dt
        )
        if track.track_id in self.staff_tracks:
            is_staff = True

        prev_centroid = self.track_prev_centroid.get(track.track_id)
        crossing = self.zone_mapper.check_line_crossing(
            camera_id, track.track_id, prev_centroid, centroid
        )
        self.track_prev_centroid[track.track_id] = centroid

        visitor_id = self.track_to_visitor.get(track.track_id)
        if visitor_id is None:
            visitor_id, is_reentry = self.reid.assign_visitor(
                crop, history, timestamp.timestamp()
            )
            self.track_to_visitor[track.track_id] = visitor_id
        else:
            is_reentry = False

        emitted = []
        if crossing == "ENTRY" and not is_staff:
            emitted.append(
                emitter.emit_entry(
                    visitor_id,
                    timestamp,
                    track.confidence,
                    is_staff,
                    {"track_id": track.track_id},
                    reentry=is_reentry,
                )
            )
        elif crossing in ("EXIT",) and not is_staff:
            self.reid.assign_visitor(
                crop,
                history,
                timestamp.timestamp(),
                is_exit=True,
                visitor_id=visitor_id,
            )
            emitted.append(
                emitter.emit_exit(
                    visitor_id,
                    timestamp,
                    track.confidence,
                    is_staff,
                    {"track_id": track.track_id},
                )
            )

        zone_id = self.zone_mapper.zone_at_point(camera_id, centroid)
        if not is_staff:
            emitted.extend(
                emitter.process_zone(track, visitor_id, zone_id, timestamp, is_staff)
            )
        return emitted

    def process_all_cameras(self) -> None:
        for camera_id in self.layout.cameras:
            self.process_camera(camera_id)
        self.bus.flush_to_api()


def _frame_timestamp(recording_date: str, frame_idx: int, fps: float) -> datetime:
    base = datetime.strptime(recording_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    seconds = frame_idx / max(fps, 1.0)
    return base + timedelta(seconds=seconds)
