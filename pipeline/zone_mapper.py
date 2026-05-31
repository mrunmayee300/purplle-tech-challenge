from __future__ import annotations

from dataclasses import dataclass, field

from shared.layout import StoreLayout, VirtualLine, ZoneDef


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi
        ):
            inside = not inside
        j = i
    return inside


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    d1 = _cross(q1, q2, p1)
    d2 = _cross(q1, q2, p2)
    d3 = _cross(p1, p2, q1)
    d4 = _cross(p1, p2, q2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


@dataclass
class LineCrossingState:
    last_side: dict[str, float] = field(default_factory=dict)


class ZoneMapper:
    def __init__(self, layout: StoreLayout) -> None:
        self.layout = layout
        self._line_state = LineCrossingState()

    def zone_at_point(
        self, camera_id: str, point: tuple[float, float]
    ) -> str | None:
        for zone in self.layout.zones_for_camera(camera_id):
            poly = zone.polygons.get(camera_id)
            if poly and point_in_polygon(point, poly):
                return zone.zone_id
        return None

    def _side_of_line(
        self, line: VirtualLine, point: tuple[float, float]
    ) -> float:
        x1, y1 = line.p1
        x2, y2 = line.p2
        return (y2 - y1) * point[0] - (x2 - x1) * point[1] + x2 * y1 - y2 * x1

    def check_line_crossing(
        self,
        camera_id: str,
        track_id: int,
        prev_centroid: tuple[float, float] | None,
        centroid: tuple[float, float],
    ) -> str | None:
        if prev_centroid is None:
            return None
        for line in self.layout.virtual_lines:
            if line.camera_id != camera_id:
                continue
            if not segments_intersect(prev_centroid, centroid, line.p1, line.p2):
                continue
            key = f"{track_id}:{line.line_id}"
            side = self._side_of_line(line, centroid)
            prev_side = self._line_state.last_side.get(key)
            self._line_state.last_side[key] = side
            if prev_side is None:
                continue
            if prev_side * side < 0:
                direction = _direction_match(line, prev_centroid, centroid)
                if direction:
                    return line.line_type.upper()
        return None


def _direction_match(
    line: VirtualLine,
    prev: tuple[float, float],
    curr: tuple[float, float],
) -> bool:
    dx = curr[0] - prev[0]
    dy = curr[1] - prev[1]
    direction = line.in_direction
    if direction == "down":
        return dy > 0.01
    if direction == "up":
        return dy < -0.01
    if direction == "left":
        return dx < -0.01
    if direction == "right":
        return dx > 0.01
    return True
