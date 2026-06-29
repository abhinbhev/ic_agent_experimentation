"""Convert an append-only stream of ``GraphEvent`` records into the
nested tree shape consumed by the live question-graph HTML component.

Output schema (matches docs/unified_question_graph_mock_v3.html TREE)::

    {
      "id": "...", "kind": "...", "label": "...",
      "status": "asked|running|answered|failed",
      "answer": "..." | None,
      "domain": "..." | None,         # only for kind == "domain"
      "round": 1 | 2 | None,          # only for kind in {"super-round","round"}
      "sublabel": "..." | None,       # only for kind == "super-round"
      "children": [ ... ]
    }
"""

from __future__ import annotations

from typing import Any

from unified_domain.observability.events import GraphEvent


def build_tree(events: list[GraphEvent]) -> dict[str, Any] | None:
    """Fold events into a nested tree dict (or None if no root event yet)."""
    if not events:
        return None

    nodes: dict[str, dict[str, Any]] = {}
    order: list[str] = []  # insertion order, used to keep child order stable

    # Latest-state-wins: emitting an event with the same node_id updates
    # status/answer/etc. but preserves the original parent_id and kind
    # (those should never change after first emit).
    for ev in events:
        existing = nodes.get(ev.node_id)
        if existing is None:
            node: dict[str, Any] = {
                "id": ev.node_id,
                "kind": ev.kind,
                "parent_id": ev.parent_id,
                "label": ev.label,
                "status": ev.status,
                "answer": ev.answer,
                "children": [],
            }
            # carry through commonly-rendered extras
            if "domain" in ev.extra:
                node["domain"] = ev.extra["domain"]
            if "round" in ev.extra:
                node["round"] = ev.extra["round"]
            if "sublabel" in ev.extra:
                node["sublabel"] = ev.extra["sublabel"]
            if "metrics" in ev.extra:
                node["metrics"] = ev.extra["metrics"]
            nodes[ev.node_id] = node
            order.append(ev.node_id)
        else:
            existing["status"] = ev.status
            if ev.label:
                existing["label"] = ev.label
            if ev.answer is not None:
                existing["answer"] = ev.answer
            # merge new extras into rendered fields
            if "sublabel" in ev.extra:
                existing["sublabel"] = ev.extra["sublabel"]
            if "metrics" in ev.extra:
                existing["metrics"] = ev.extra["metrics"]

    # Wire children, preserving insertion order
    root: dict[str, Any] | None = None
    for nid in order:
        n = nodes[nid]
        pid = n.get("parent_id")
        if pid is None:
            if root is None:
                root = n
        else:
            parent = nodes.get(pid)
            if parent is not None:
                parent["children"].append(n)

    # strip parent_id from final output — UI doesn't need it
    for n in nodes.values():
        n.pop("parent_id", None)

    return root
