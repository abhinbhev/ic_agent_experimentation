"""Helpers that emit ``GraphEvent`` records as super-agent and
sub-agent nodes execute. Kept in its own module so node factories
stay readable.

Public entry points:

* ``emit_super_round_start(bus, round_idx, sublabel)``
* ``emit_super_probes(bus, round_idx, consultant_plan)``
* ``emit_domain_assignments(bus, round_idx, assignments)``
* ``emit_super_round_done(bus, round_idx)``
* ``stream_subagent_events(bus, app, initial_state, *, parent_domain_node_id, probe_candidate_id, ...)``

ID conventions match the design spec::

    root                        "root"
    super-round                 "SR{round_idx}"            (1-indexed)
    super-probe                 "{probe_candidate_id}"     (e.g. "P1")
    domain                      "{probe_id}-{short_domain}" (e.g. "P1-bg")
    round (sub-agent)           "{domain_node_id}-R{n}"
    sub-probe                   "{round_node_id}-s{n}"
    leaf retrieval              "{subprobe_node_id}-r{n}"
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from unified_domain.models.domain_router import DomainAssignment
    from unified_domain.models.planner_consultant import (
        UnifiedPlannerConsultantOutput,
    )
    from unified_domain.observability.event_bus import EventBus

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# ID helpers
# --------------------------------------------------------------------- #

_SHORT_DOMAIN_OVERRIDES = {
    "gai_copilot_marketing_brand_guidance_ghq": "bg",
    "gai_copilot_marketing_category_ghq": "cat",
}


def short_domain(domain_id: str) -> str:
    if domain_id in _SHORT_DOMAIN_OVERRIDES:
        return _SHORT_DOMAIN_OVERRIDES[domain_id]
    # fallback: first letter of each underscore-separated segment, up to 4 chars
    parts = [p for p in re.split(r"[_\-]", domain_id) if p]
    if not parts:
        return domain_id[:4]
    return "".join(p[0] for p in parts[:4]).lower() or domain_id[:4]


def super_round_id(round_idx_1based: int) -> str:
    return f"SR{round_idx_1based}"


def domain_node_id(probe_candidate_id: str, domain_id: str) -> str:
    return f"{probe_candidate_id}-{short_domain(domain_id)}"


# --------------------------------------------------------------------- #
# Super-agent emitters
# --------------------------------------------------------------------- #


def emit_root(bus: "EventBus | None", query: str) -> None:
    if bus is None:
        return
    bus.emit("root", None, "root", "asked", label=query)


def emit_root_answered(bus: "EventBus | None", answer: str) -> None:
    if bus is None:
        return
    bus.emit("root", None, "root", "answered", label="", answer=_short(answer))


def emit_super_round_start(
    bus: "EventBus | None",
    round_idx_1based: int,
    sublabel: str = "",
) -> str:
    sr_id = super_round_id(round_idx_1based)
    if bus is not None:
        bus.emit(
            sr_id,
            "root",
            "super-round",
            "running",
            label=f"Super-Round {round_idx_1based}",
            extra={"round": round_idx_1based, "sublabel": sublabel},
        )
    return sr_id


def emit_super_round_done(bus: "EventBus | None", round_idx_1based: int) -> None:
    if bus is None:
        return
    sr_id = super_round_id(round_idx_1based)
    bus.emit(
        sr_id,
        "root",
        "super-round",
        "answered",
        label=f"Super-Round {round_idx_1based}",
        extra={"round": round_idx_1based},
    )


def emit_round_metrics(
    bus: "EventBus | None",
    round_node_id: str,
    parent_id: str | None,
    kind: str,
    round_idx_1based: int,
    decision_engine_output: Any,
) -> None:
    """Attach Decision Engine stop-condition metrics to a round/super-round node.

    Re-emits the node with the latest known label/status and adds a
    ``metrics`` payload under ``extra`` for the UI to render as a badge.
    Pulls fields off the output dynamically so this works for both the
    single-agent and unified ``DecisionEngineOutput`` shapes.
    """
    if bus is None or decision_engine_output is None:
        return
    out = decision_engine_output
    breakdown = getattr(out, "value_breakdown", None)
    breakdown_dict: dict[str, Any] = {}
    if breakdown is not None and hasattr(breakdown, "model_dump"):
        breakdown_dict = breakdown.model_dump()
    elif isinstance(breakdown, dict):
        breakdown_dict = dict(breakdown)
    metrics = {
        "stop_reason": getattr(out, "stop_reason", ""),
        "continue": bool(getattr(out, "continue_", False)),
        "ivf": float(getattr(out, "expected_incremental_value", 0.0) or 0.0),
        "recommended_next_gap": getattr(out, "recommended_next_gap", None),
        "reason": getattr(out, "reason", ""),
        "breakdown": breakdown_dict,
    }
    label = (
        f"Super-Round {round_idx_1based}" if kind == "super-round" else f"Round {round_idx_1based}"
    )
    bus.emit(
        round_node_id,
        parent_id,
        kind,  # type: ignore[arg-type]
        "answered",
        label=label,
        extra={"round": round_idx_1based, "metrics": metrics},
    )


def emit_super_probes(
    bus: "EventBus | None",
    round_idx_1based: int,
    plan: "UnifiedPlannerConsultantOutput",
) -> None:
    if bus is None:
        return
    sr_id = super_round_id(round_idx_1based)
    for pc in plan.probe_candidates:
        bus.emit(
            pc.id,
            sr_id,
            "super-probe",
            "asked",
            label=pc.goal,
            extra={"expected_value": pc.expected_value, "round": round_idx_1based},
        )


def emit_domain_assignments(
    bus: "EventBus | None",
    assignments: list["DomainAssignment"],
) -> None:
    if bus is None:
        return
    for a in assignments:
        for probe in a.probes:
            dn_id = domain_node_id(probe.probe_candidate_id, probe.domain_id)
            bus.emit(
                dn_id,
                probe.probe_candidate_id,
                "domain",
                "asked",
                label=probe.scoped_question,
                extra={"domain": short_domain(probe.domain_id), "domain_id": probe.domain_id},
            )


def emit_super_probe_status(
    bus: "EventBus | None",
    probe_candidate_id: str,
    status: str,
    answer: str | None = None,
) -> None:
    if bus is None:
        return
    bus.emit(
        probe_candidate_id,
        None,  # parent already set on creation
        "super-probe",
        status,  # type: ignore[arg-type]
        answer=_short(answer) if answer else None,
    )


def emit_domain_status(
    bus: "EventBus | None",
    probe_candidate_id: str,
    domain_id: str,
    status: str,
    answer: str | None = None,
) -> None:
    if bus is None:
        return
    dn_id = domain_node_id(probe_candidate_id, domain_id)
    bus.emit(
        dn_id,
        probe_candidate_id,
        "domain",
        status,  # type: ignore[arg-type]
        answer=_short(answer) if answer else None,
        extra={"domain": short_domain(domain_id)},
    )


# --------------------------------------------------------------------- #
# Sub-agent streaming instrumentation
# --------------------------------------------------------------------- #


async def stream_subagent_run(
    bus: "EventBus | None",
    app: Any,
    initial_state: dict[str, Any],
    *,
    parent_domain_node_id: str,
    probe_candidate_id: str,
    domain_id: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a single-agent graph via ``app.astream`` and emit events.

    Returns the final state (last seen step's merged values) for use
    by the caller (DomainAgentExecutor).
    """
    config = config or {"recursion_limit": 100}

    # Sub-agent local state (used to build IDs for rounds / probes / leaves
    # as they appear in the stream).
    state: dict[str, Any] = {}
    round_idx = 0  # 1-indexed when emitted
    current_round_node_id: str | None = None
    last_known_evidence_count = 0
    sub_probe_count_this_round = 0
    sub_probe_node_ids: list[str] = []  # ids emitted this round, in order

    # If no bus, fall back to plain ainvoke so behaviour is identical.
    if bus is None:
        return await app.ainvoke(initial_state, config=config)

    async for step in app.astream(initial_state, config=config):
        for node_name, update in step.items():
            # Always merge into accumulated state
            if isinstance(update, dict):
                state.update(update)

            if node_name == "planner_consultant":
                round_idx += 1
                current_round_node_id = f"{parent_domain_node_id}-R{round_idx}"
                sub_probe_count_this_round = 0
                sub_probe_node_ids = []
                bus.emit(
                    current_round_node_id,
                    parent_domain_node_id,
                    "round",
                    "running",
                    label=f"Round {round_idx}",
                    extra={"round": round_idx},
                )

            elif node_name == "planner":
                # planner produces tool_calls (questions) — emit sub-probe + leaf for each
                tool_calls = update.get("tool_calls", []) if isinstance(update, dict) else []
                if current_round_node_id is None:
                    # Defensive: synthesise a round if planner_consultant wasn't seen
                    round_idx = max(round_idx, 1)
                    current_round_node_id = f"{parent_domain_node_id}-R{round_idx}"
                    bus.emit(
                        current_round_node_id,
                        parent_domain_node_id,
                        "round",
                        "running",
                        label=f"Round {round_idx}",
                        extra={"round": round_idx},
                    )
                sub_probe_node_ids = []
                for i, tc in enumerate(tool_calls, start=1):
                    sub_probe_count_this_round += 1
                    sp_id = f"{current_round_node_id}-s{sub_probe_count_this_round}"
                    sub_probe_node_ids.append(sp_id)
                    question = getattr(tc, "question", "") or ""
                    bus.emit(
                        sp_id,
                        current_round_node_id,
                        "sub-probe",
                        "running",
                        label=question,
                    )
                    # leaf retrieval — same question text
                    leaf_id = f"{sp_id}-r1"
                    bus.emit(
                        leaf_id,
                        sp_id,
                        "leaf",
                        "running",
                        label=question,
                    )

            elif node_name == "execution":
                # execution appended new EvidenceLedgerEntry rows.
                ledger = state.get("evidence_ledger", []) or []
                new_entries = ledger[last_known_evidence_count:]
                last_known_evidence_count = len(ledger)
                # Pair new entries with the sub-probes we just emitted (1-to-1).
                for entry, sp_id in zip(new_entries, sub_probe_node_ids):
                    leaf_id = f"{sp_id}-r1"
                    answer = _short(getattr(entry, "result", "") or "")
                    bus.emit(
                        leaf_id,
                        sp_id,
                        "leaf",
                        "answered",
                        answer=answer,
                    )
                    bus.emit(
                        sp_id,
                        current_round_node_id,
                        "sub-probe",
                        "answered",
                        answer=answer,
                    )
                # round done (a planner_consultant for next round would re-open it)
                if current_round_node_id is not None:
                    bus.emit(
                        current_round_node_id,
                        parent_domain_node_id,
                        "round",
                        "answered",
                        label=f"Round {round_idx}",
                        extra={"round": round_idx},
                    )

            elif node_name == "decision_engine":
                de_out = update.get("decision_engine_output") if isinstance(update, dict) else None
                if de_out is not None and current_round_node_id is not None:
                    emit_round_metrics(
                        bus,
                        current_round_node_id,
                        parent_domain_node_id,
                        "round",
                        round_idx,
                        de_out,
                    )

            elif node_name == "synthesis":
                final = update.get("final_answer") if isinstance(update, dict) else None
                if final is not None:
                    answer = _short(getattr(final, "markdown", "") or "")
                    bus.emit(
                        parent_domain_node_id,
                        probe_candidate_id,
                        "domain",
                        "answered",
                        answer=answer,
                        extra={"domain": short_domain(domain_id)},
                    )

    return state


# --------------------------------------------------------------------- #
# misc
# --------------------------------------------------------------------- #


def _short(text: str, limit: int = 180) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.strip().split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"
