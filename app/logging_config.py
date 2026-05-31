from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "trace_id"):
            payload["trace_id"] = record.trace_id
        for key in ("store_id", "endpoint", "latency_ms", "event_count", "status_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        store_id = request.path_params.get("id") or request.query_params.get("store_id")
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logging.getLogger("api").error(
                "request_failed",
                extra={
                    "trace_id": trace_id,
                    "store_id": store_id,
                    "endpoint": request.url.path,
                    "latency_ms": latency_ms,
                    "event_count": 0,
                    "status_code": 500,
                },
            )
            raise
        latency_ms = int((time.perf_counter() - start) * 1000)
        event_count = int(response.headers.get("X-Event-Count", "0"))
        logging.getLogger("api").info(
            "request_complete",
            extra={
                "trace_id": trace_id,
                "store_id": store_id,
                "endpoint": request.url.path,
                "latency_ms": latency_ms,
                "event_count": event_count,
                "status_code": response.status_code,
            },
        )
        response.headers["X-Trace-Id"] = trace_id
        return response
