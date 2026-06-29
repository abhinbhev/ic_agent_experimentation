"""Thread-safe event bus for the live question graph.

Designed to be created per super-agent run, passed into the unified
``AgentState``, and read by the UI on a poll loop.

Usage::

    bus = EventBus()
    bus.emit("root", None, "root", "asked", label="...")
    snapshot = bus.snapshot()  # list[GraphEvent], independent copy
"""

from __future__ import annotations

import threading
import time
from typing import Any

from unified_domain.observability.events import GraphEvent, NodeKind, NodeStatus


class EventBus:
    """Append-only, thread-safe collector of ``GraphEvent`` records."""

    def __init__(self) -> None:
        self._events: list[GraphEvent] = []
        self._lock = threading.Lock()
        self._version = 0  # monotonic counter — UI can use it to detect changes

    def emit(
        self,
        node_id: str,
        parent_id: str | None,
        kind: NodeKind,
        status: NodeStatus,
        *,
        label: str = "",
        answer: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> GraphEvent:
        event = GraphEvent(
            ts=time.time(),
            node_id=node_id,
            parent_id=parent_id,
            kind=kind,
            status=status,
            label=label,
            answer=answer,
            extra=dict(extra or {}),
        )
        with self._lock:
            self._events.append(event)
            self._version += 1
        return event

    def snapshot(self) -> list[GraphEvent]:
        with self._lock:
            return list(self._events)

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._version += 1
