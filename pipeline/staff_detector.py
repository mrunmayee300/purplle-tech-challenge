from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from shared.layout import StoreLayout


@dataclass
class TrackProfile:
    appearances: int = 0
    total_dwell_seconds: float = 0.0
    zones: set[str] = field(default_factory=set)
    uniform_score: float = 0.0
    is_staff: bool = False


class StaffDetector:
    """Uniform color clustering + frequent long multi-zone appearance heuristic."""

    def __init__(self, layout: StoreLayout) -> None:
        from shared.config import (
            STAFF_MIN_APPEARANCES,
            STAFF_MIN_DWELL_SECONDS,
            STAFF_MIN_ZONES,
        )

        self.uniform_specs = layout.staff_uniform_colors
        self.min_appearances = STAFF_MIN_APPEARANCES
        self.min_dwell_seconds = STAFF_MIN_DWELL_SECONDS
        self.min_zones = STAFF_MIN_ZONES
        self.profiles: dict[int, TrackProfile] = defaultdict(TrackProfile)
        self._uniform_cluster_hits: dict[int, int] = defaultdict(int)

    def observe(
        self,
        track_id: int,
        crop: np.ndarray,
        zone_id: str | None,
        dt_seconds: float,
    ) -> bool:
        profile = self.profiles[track_id]
        profile.appearances += 1
        profile.total_dwell_seconds += dt_seconds
        if zone_id:
            profile.zones.add(zone_id)
        uniform_hit = self._uniform_color_match(crop)
        if uniform_hit:
            self._uniform_cluster_hits[track_id] += 1
            profile.uniform_score = min(
                1.0, profile.uniform_score + 0.05
            )
        profile.is_staff = self._classify(profile, track_id)
        return profile.is_staff

    def _uniform_color_match(self, crop: np.ndarray) -> bool:
        if crop.size == 0:
            return False
        import cv2

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        torso = hsv[int(hsv.shape[0] * 0.2) : int(hsv.shape[0] * 0.65), :]
        if torso.size == 0:
            torso = hsv
        median = np.median(torso.reshape(-1, 3), axis=0)
        h, s, v = median
        for spec in self.uniform_specs:
            if (
                spec["h_min"] <= h <= spec["h_max"]
                and spec["s_min"] <= s <= spec["s_max"]
                and spec["v_min"] <= v <= spec["v_max"]
            ):
                return True
            if spec["name"] == "black_uniform" and v <= spec["v_max"]:
                return True
        return False

    def _classify(self, profile: TrackProfile, track_id: int) -> bool:
        frequent = (
            profile.appearances >= self.min_appearances
            and profile.total_dwell_seconds >= self.min_dwell_seconds
            and len(profile.zones) >= self.min_zones
        )
        uniform_cluster = self._uniform_cluster_hits[track_id] >= 15
        return frequent or uniform_cluster or profile.uniform_score >= 0.45

    def finalize(self) -> set[int]:
        staff_ids: set[int] = set()
        for track_id, profile in self.profiles.items():
            profile.is_staff = self._classify(profile, track_id)
            if profile.is_staff:
                staff_ids.add(track_id)
        return staff_ids
