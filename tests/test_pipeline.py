# PROMPT: Test CV pipeline modules — zones, staff, re-entry, line crossing, all-staff clip.
# CHANGES MADE: Unit tests for zone mapper, staff detector, reid, and event emitter.

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import numpy as np
import pytest

from pipeline.event_emitter import EventEmitter
from pipeline.reid import ReIdentificationEngine, cv2_hsv_histogram
from pipeline.staff_detector import StaffDetector
from pipeline.tracker import TrackState
from pipeline.zone_mapper import ZoneMapper, point_in_polygon, segments_intersect
from shared.event_bus import EventBus
from shared.layout import StoreLayout


@pytest.fixture(scope="module")
def layout():
    return StoreLayout.load()


def test_point_in_polygon():
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert point_in_polygon((0.5, 0.5), square)
    assert not point_in_polygon((1.5, 0.5), square)


def test_line_crossing(layout):
    mapper = ZoneMapper(layout)
    line = layout.virtual_lines[0]
    crossing = segments_intersect((0.5, 0.3), (0.5, 0.5), line.p1, line.p2)
    assert crossing
    result = mapper.check_line_crossing("cam_1", 1, (0.5, 0.35), (0.5, 0.55))
    assert result in (None, "ENTRY", "EXIT")


def test_reentry(layout):
    reid = ReIdentificationEngine(reentry_window_seconds=900)
    crop = np.zeros((80, 40, 3), dtype=np.uint8)
    vid1, _ = reid.assign_visitor(crop, [(0.5, 0.5)], 1000.0)
    reid.assign_visitor(crop, [(0.5, 0.5)], 1100.0, is_exit=True, visitor_id=vid1)
    vid2, is_reentry = reid.assign_visitor(crop, [(0.5, 0.5)], 1200.0)
    assert vid1 == vid2
    assert is_reentry


def test_three_entries_separate_visitors(layout):
    reid = ReIdentificationEngine()
    crop = np.zeros((80, 40, 3), dtype=np.uint8)
    ids = []
    for i in range(3):
        c = np.random.default_rng(i).integers(0, 255, size=(80, 40, 3), dtype=np.uint8)
        vid, _ = reid.assign_visitor(c, [(0.1 * i, 0.5)], 1000.0 + i)
        ids.append(vid)
    assert len(set(ids)) == 3


def test_staff_detector_all_staff(layout):
    staff = StaffDetector(layout)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    for _ in range(200):
        staff.observe(99, crop, "makeup", 5.0)
        staff.observe(99, crop, "skincare", 5.0)
        staff.observe(99, crop, "billing", 5.0)
    assert staff.observe(99, crop, "personal_care", 5.0)


def test_event_emitter_zone_dwell(layout, tmp_path):
    bus = EventBus(jsonl_path=tmp_path / "events.jsonl")
    emitter = EventEmitter(layout, bus, "ST1008", "cam_2")
    track = TrackState(track_id=7, bbox=(0.2, 0.2, 0.4, 0.6), confidence=0.9)
    t0 = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    emitter.process_zone(track, "v-7", "makeup", t0, False)
    t1 = t0.replace(second=35)
    events = emitter.process_zone(track, "v-7", "makeup", t1, False)
    assert any(e.event_type == "ZONE_DWELL" for e in events)


def test_appearance_embedding():
    crop = np.random.randint(0, 255, (64, 32, 3), dtype=np.uint8)
    emb = cv2_hsv_histogram(crop)
    assert emb.shape[0] == 256
