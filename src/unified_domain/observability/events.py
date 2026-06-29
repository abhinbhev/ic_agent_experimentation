"""GraphEvent and related enums for the live question graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

NodeKind = Literal[
    "root",
    "super-round",
    "super-probe",
    "domain",
    "round",
    "sub-probe",
    "leaf",
]

NodeStatus = Literal["asked", "running", "answered", "failed"]


@dataclass
class GraphEvent:
    """One state-change emitted by a unified- or single-agent node.

    Events are append-only — to record a status change for an existing
    node, emit a fresh event with the same ``node_id`` and the new
    ``status``. The tree builder collapses these to the latest status.
    """

    ts: float
    node_id: str
    parent_id: str | None
    kind: NodeKind
    status: NodeStatus
    label: str = ""
    answer: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "kind": self.kind,
            "status": self.status,
            "label": self.label,
            "answer": self.answer,
            "extra": dict(self.extra),
        }
