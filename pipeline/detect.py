from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from shared.config import PIPELINE_DEVICE, YOLO_CONF, YOLO_IOU, YOLO_MODEL


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # xyxy normalized
    confidence: float
    class_id: int = 0


class PersonDetector:
    """YOLOv8 person detector (class 0 = person in COCO)."""

    def __init__(
        self,
        model_name: str = YOLO_MODEL,
        conf: float = YOLO_CONF,
        iou: float = YOLO_IOU,
        device: str = PIPELINE_DEVICE,
    ) -> None:
        self.conf = conf
        self.iou = iou
        self.device = device
        from ultralytics import YOLO

        self.model = YOLO(model_name)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        results = self.model.predict(
            frame,
            conf=self.conf,
            iou=self.iou,
            classes=[0],
            verbose=False,
            device=self.device,
        )
        detections: list[Detection] = []
        if not results:
            return detections
        boxes = results[0].boxes
        if boxes is None:
            return detections
        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            x1, y1, x2, y2 = xyxy
            detections.append(
                Detection(
                    bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                    confidence=conf,
                    class_id=0,
                )
            )
        return detections

    def detect_batch(self, frames: list[np.ndarray]) -> list[list[Detection]]:
        return [self.detect(frame) for frame in frames]
