from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from shared.config import API_BASE_URL
from shared.events import StoreEvent

logger = logging.getLogger(__name__)


class EventBus:
    """Internal pub/sub bus with JSONL persistence and optional API fan-out."""

    def __init__(
        self,
        jsonl_path: Path | None = None,
        api_url: str | None = None,
        batch_size: int = 100,
    ) -> None:
        self._subscribers: list[Callable[[StoreEvent], None]] = []
        self._lock = threading.Lock()
        self._buffer: list[StoreEvent] = []
        self.jsonl_path = jsonl_path
        self.api_url = api_url or f"{API_BASE_URL}/events/ingest"
        self.batch_size = batch_size
        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, handler: Callable[[StoreEvent], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: StoreEvent) -> None:
        with self._lock:
            self._buffer.append(event)
            if self.jsonl_path:
                with self.jsonl_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict()) + "\n")
            for handler in self._subscribers:
                handler(event)

    def flush_to_api(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._buffer:
                return None
            batch = self._buffer[:]
            self._buffer.clear()
        payload = {"events": [e.to_dict() for e in batch]}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning("API ingest failed: %s", exc)
            if self.jsonl_path:
                with self.jsonl_path.open("a", encoding="utf-8") as f:
                    for event in batch:
                        f.write(json.dumps(event.to_dict()) + "\n")
            return None

    def publish_batch(self, events: list[StoreEvent]) -> None:
        for event in events:
            self.publish(event)
