from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pipeline.detect import Detection


@dataclass
class TrackState:
    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    history: list[tuple[float, float]] = field(default_factory=list)

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)


class ByteTrackerWrapper:
    """ByteTrack multi-object tracker with persistent IDs."""

    def __init__(self) -> None:
        import supervision as sv

        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=30,
        )

    def update(
        self, detections: list[Detection], frame_shape: tuple[int, int]
    ) -> list[TrackState]:
        import supervision as sv

        h, w = frame_shape
        if not detections:
            tracked = self.tracker.update_with_detections(
                sv.Detections.empty()
            )
        else:
            xyxy = np.array(
                [
                    [
                        d.bbox[0] * w,
                        d.bbox[1] * h,
                        d.bbox[2] * w,
                        d.bbox[3] * h,
                    ]
                    for d in detections
                ],
                dtype=np.float32,
            )
            confidences = np.array([d.confidence for d in detections], dtype=np.float32)
            class_ids = np.zeros(len(detections), dtype=int)
            dets = sv.Detections(
                xyxy=xyxy,
                confidence=confidences,
                class_id=class_ids,
            )
            tracked = self.tracker.update_with_detections(dets)

        states: list[TrackState] = []
        if tracked.tracker_id is None:
            return states
        for i, tid in enumerate(tracked.tracker_id):
            if tid is None:
                continue
            box = tracked.xyxy[i]
            bbox = (box[0] / w, box[1] / h, box[2] / w, box[3] / h)
            conf = float(tracked.confidence[i]) if tracked.confidence is not None else 0.5
            state = TrackState(track_id=int(tid), bbox=bbox, confidence=conf)
            state.history.append(state.centroid)
            states.append(state)
        return states
