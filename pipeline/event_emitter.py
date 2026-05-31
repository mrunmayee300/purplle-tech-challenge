from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pipeline.tracker import TrackState
from shared.event_bus import EventBus
from shared.events import StoreEvent, new_event
from shared.layout import StoreLayout


class EventEmitter:
    def __init__(
        self,
        layout: StoreLayout,
        bus: EventBus,
        store_id: str,
        camera_id: str,
    ) -> None:
        self.layout = layout
        self.bus = bus
        self.store_id = store_id
        self.camera_id = camera_id
        self._zone_entered: dict[int, str | None] = {}
        self._last_dwell_emit: dict[tuple[int, str], datetime] = {}
        self._zone_enter_time: dict[tuple[int, str], datetime] = {}
        self._billing_queue: set[int] = set()
        self._billing_join_time: dict[int, datetime] = {}
        self._visitor_purchased: set[str] = set()

    def emit_entry(
        self,
        visitor_id: str,
        timestamp: datetime,
        confidence: float,
        is_staff: bool,
        metadata: dict[str, Any] | None = None,
        reentry: bool = False,
    ) -> StoreEvent:
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="REENTRY" if reentry else "ENTRY",
            timestamp=timestamp,
            zone_id="entry",
            is_staff=is_staff,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.bus.publish(event)
        return event

    def emit_exit(
        self,
        visitor_id: str,
        timestamp: datetime,
        confidence: float,
        is_staff: bool,
        metadata: dict[str, Any] | None = None,
    ) -> StoreEvent:
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="EXIT",
            timestamp=timestamp,
            zone_id="exit_lane",
            is_staff=is_staff,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.bus.publish(event)
        return event

    def process_zone(
        self,
        track: TrackState,
        visitor_id: str,
        zone_id: str | None,
        timestamp: datetime,
        is_staff: bool,
    ) -> list[StoreEvent]:
        events: list[StoreEvent] = []
        prev_zone = self._zone_entered.get(track.track_id)
        if zone_id == prev_zone:
            events.extend(
                self._maybe_dwell(track.track_id, visitor_id, zone_id, timestamp, is_staff)
            )
            return events
        if prev_zone:
            events.append(self._zone_exit(track, visitor_id, prev_zone, timestamp, is_staff))
        if zone_id:
            events.append(self._zone_enter(track, visitor_id, zone_id, timestamp, is_staff))
            self._zone_enter_time[(track.track_id, zone_id)] = timestamp
            self._last_dwell_emit[(track.track_id, zone_id)] = timestamp
        self._zone_entered[track.track_id] = zone_id
        return events

    def _zone_enter(
        self,
        track: TrackState,
        visitor_id: str,
        zone_id: str,
        timestamp: datetime,
        is_staff: bool,
    ) -> StoreEvent:
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="ZONE_ENTER",
            timestamp=timestamp,
            zone_id=zone_id,
            is_staff=is_staff,
            confidence=track.confidence,
            metadata={"track_id": track.track_id},
        )
        self.bus.publish(event)
        if zone_id == self.layout.billing_queue_zone_id:
            self._handle_billing_join(track, visitor_id, timestamp, is_staff)
        return event

    def _zone_exit(
        self,
        track: TrackState,
        visitor_id: str,
        zone_id: str,
        timestamp: datetime,
        is_staff: bool,
    ) -> StoreEvent:
        enter_time = self._zone_enter_time.pop((track.track_id, zone_id), timestamp)
        dwell_ms = int((timestamp - enter_time).total_seconds() * 1000)
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="ZONE_EXIT",
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=is_staff,
            confidence=track.confidence,
            metadata={"track_id": track.track_id},
        )
        self.bus.publish(event)
        if (
            zone_id in (self.layout.billing_zone_id, self.layout.billing_queue_zone_id)
            and track.track_id in self._billing_queue
            and visitor_id not in self._visitor_purchased
            and not is_staff
        ):
            self._emit_queue_abandon(track, visitor_id, timestamp)
        if track.track_id in self._billing_queue:
            self._billing_queue.discard(track.track_id)
        return event

    def _maybe_dwell(
        self,
        track_id: int,
        visitor_id: str,
        zone_id: str,
        timestamp: datetime,
        is_staff: bool,
    ) -> list[StoreEvent]:
        interval = self.layout.dwell_emit_interval_seconds
        key = (track_id, zone_id)
        last = self._last_dwell_emit.get(key)
        if last is None:
            self._last_dwell_emit[key] = timestamp
            return []
        if (timestamp - last).total_seconds() < interval:
            return []
        enter_time = self._zone_enter_time.get(key, last)
        dwell_ms = int((timestamp - enter_time).total_seconds() * 1000)
        self._last_dwell_emit[key] = timestamp
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="ZONE_DWELL",
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=is_staff,
            confidence=0.8,
            metadata={"track_id": track_id},
        )
        self.bus.publish(event)
        return [event]

    def _handle_billing_join(
        self,
        track: TrackState,
        visitor_id: str,
        timestamp: datetime,
        is_staff: bool,
    ) -> StoreEvent:
        self._billing_queue.add(track.track_id)
        self._billing_join_time[track.track_id] = timestamp
        depth = len(self._billing_queue)
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="BILLING_QUEUE_JOIN",
            timestamp=timestamp,
            zone_id=self.layout.billing_queue_zone_id,
            is_staff=is_staff,
            confidence=track.confidence,
            metadata={"queue_depth": depth, "track_id": track.track_id},
        )
        self.bus.publish(event)
        return event

    def _emit_queue_abandon(
        self,
        track: TrackState,
        visitor_id: str,
        timestamp: datetime,
    ) -> StoreEvent:
        event = new_event(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type="BILLING_QUEUE_ABANDON",
            timestamp=timestamp,
            zone_id=self.layout.billing_queue_zone_id,
            is_staff=False,
            confidence=track.confidence,
            metadata={"track_id": track.track_id, "reason": "left_without_purchase"},
        )
        self.bus.publish(event)
        return event

    def mark_purchase(self, visitor_id: str) -> None:
        self._visitor_purchased.add(visitor_id)

    def queue_depth(self) -> int:
        return len(self._billing_queue)
