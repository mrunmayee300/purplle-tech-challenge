from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.config import LAYOUT_PATH


@dataclass
class VirtualLine:
    line_id: str
    camera_id: str
    line_type: str
    p1: tuple[float, float]
    p2: tuple[float, float]
    in_direction: str


@dataclass
class ZoneDef:
    zone_id: str
    name: str
    zone_type: str
    cameras: list[str]
    polygons: dict[str, list[tuple[float, float]]]


class StoreLayout:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.store_id = data["store_id"]
        self.store_name = data.get("store_name", "")
        self.cameras = {c["camera_id"]: c for c in data["cameras"]}
        self.zones: dict[str, ZoneDef] = {}
        for z in data["zones"]:
            polys = {
                cam: [tuple(p) for p in poly]
                for cam, poly in z["polygons"].items()
            }
            self.zones[z["zone_id"]] = ZoneDef(
                zone_id=z["zone_id"],
                name=z["name"],
                zone_type=z.get("type", "generic"),
                cameras=z.get("cameras", list(polys.keys())),
                polygons=polys,
            )
        self.virtual_lines = [
            VirtualLine(
                line_id=line["line_id"],
                camera_id=line["camera_id"],
                line_type=line["type"],
                p1=tuple(line["p1"]),
                p2=tuple(line["p2"]),
                in_direction=line["in_direction"],
            )
            for line in data.get("virtual_lines", [])
        ]
        billing = data.get("billing", {})
        self.billing_zone_id = billing.get("zone_id", "billing")
        self.billing_queue_zone_id = billing.get("queue_zone_id", "billing_queue")
        self.billing_camera_id = billing.get("camera_id", "cam_4")
        self.reentry_window_seconds = int(
            data.get("reentry_window_seconds", 900)
        )
        self.dwell_emit_interval_seconds = int(
            data.get("dwell_emit_interval_seconds", 30)
        )
        self.staff_uniform_colors = data.get("staff_uniform_colors_hsv", [])

    @classmethod
    def load(cls, path: Path | None = None) -> "StoreLayout":
        layout_path = path or LAYOUT_PATH
        with layout_path.open(encoding="utf-8") as f:
            return cls(json.load(f))

    def zones_for_camera(self, camera_id: str) -> list[ZoneDef]:
        return [z for z in self.zones.values() if camera_id in z.polygons]

    def video_path(self, camera_id: str, video_root: Path) -> Path:
        cam = self.cameras[camera_id]
        return video_root / cam["video_file"]
