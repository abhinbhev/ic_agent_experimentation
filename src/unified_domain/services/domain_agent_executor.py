"""Domain Agent Executor — runs single-domain agent graphs in parallel.

Replaces the single-agent Execution node. For each ``DomainAssignment``
the executor builds a complete single-domain LangGraph app via
``build_app`` and invokes it with the probe's scoped question.
Domains run concurrently via ``asyncio.gather``; probes within a domain
run sequentially.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.settings import Settings, get_settings
from ic_agent.graph.build_graph import build_app
from ic_agent.models.domain import DomainConfig
from ic_agent.utils.ids import new_probe_id
from ic_agent.utils.timing import now_iso
from unified_domain.models.domain_router import DomainAssignment, DomainProbe
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.observability import instrumentation as obs

if TYPE_CHECKING:  # pragma: no cover
    from unified_domain.observability import EventBus

logger = logging.getLogger(__name__)


class DomainAgentExecutor:
    """Orchestrates parallel single-domain agent runs."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        assignments: list[DomainAssignment],
        round_index: int = 0,
        *,
        event_bus: "EventBus | None" = None,
    ) -> list[UnifiedEvidenceLedgerEntry]:
        """Run single-domain agents in parallel for each assignment."""
        logger.info(
            "DomainAgentExecutor: dispatching %d domain(s) in parallel",
            len(assignments),
        )
        results = await asyncio.gather(
            *[self._run_domain(a, round_index, event_bus) for a in assignments]
        )
        flat: list[UnifiedEvidenceLedgerEntry] = [
            entry for domain_entries in results for entry in domain_entries
        ]
        logger.info(
            "DomainAgentExecutor: all domains completed, %d entries total",
            len(flat),
        )
        return flat

    def execute_sync(
        self,
        assignments: list[DomainAssignment],
        round_index: int = 0,
        *,
        event_bus: "EventBus | None" = None,
    ) -> list[UnifiedEvidenceLedgerEntry]:
        """Synchronous wrapper for environments without an event loop."""
        return asyncio.run(self.execute(assignments, round_index, event_bus=event_bus))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_domain(
        self,
        assignment: DomainAssignment,
        round_index: int,
        event_bus: "EventBus | None",
    ) -> list[UnifiedEvidenceLedgerEntry]:
        """Run all probes for a single domain sequentially."""
        domain_id = assignment.domain_id
        logger.info(
            "DomainAgentExecutor: starting domain=%s with %d probe(s)",
            domain_id,
            len(assignment.probes),
        )
        t0 = time.perf_counter()

        domain_config = load_domain_config(domain_id, self._settings.domain_config_dir)

        entries: list[UnifiedEvidenceLedgerEntry] = []
        for probe in assignment.probes:
            # Mark this domain node as running before its sub-agent starts
            obs.emit_domain_status(event_bus, probe.probe_candidate_id, probe.domain_id, "running")
            entry = await self._run_single_probe(probe, domain_config, round_index, event_bus)
            entries.append(entry)

        elapsed = time.perf_counter() - t0
        logger.info(
            "DomainAgentExecutor: domain=%s completed in %.1fs with %d entries",
            domain_id,
            elapsed,
            len(entries),
        )
        return entries

    async def _run_single_probe(
        self,
        probe: DomainProbe,
        domain_config: DomainConfig,
        round_index: int,
        event_bus: "EventBus | None",
    ) -> UnifiedEvidenceLedgerEntry:
        """Run one single-domain agent for one probe question."""
        logger.info(
            "DomainAgentExecutor: running probe %s on domain=%s: %s",
            probe.probe_candidate_id,
            probe.domain_id,
            probe.scoped_question[:80],
        )

        try:
            app = build_app(domain_config, self._settings)
            initial_state = {
                "query": probe.scoped_question,
                "domain_config": domain_config,
            }

            parent_domain_node_id = obs.domain_node_id(probe.probe_candidate_id, probe.domain_id)

            # Stream sub-agent execution and emit events as each node fires.
            # If event_bus is None this falls back to a plain ainvoke and the
            # final state is returned unchanged.
            final_state = await obs.stream_subagent_run(
                event_bus,
                app,
                initial_state,
                parent_domain_node_id=parent_domain_node_id,
                probe_candidate_id=probe.probe_candidate_id,
                domain_id=probe.domain_id,
                config={"recursion_limit": 100},
            )

            final_answer = final_state.get("final_answer")
            result = final_answer.markdown if final_answer else ""

            sub_evidence = final_state.get("evidence_ledger", [])

            return UnifiedEvidenceLedgerEntry(
                probe_id=new_probe_id(),
                question=probe.scoped_question,
                source_domain_id=probe.domain_id,
                result=result,
                sub_evidence=sub_evidence,
                round_index=round_index,
                created_at=now_iso(),
            )

        except Exception as exc:
            logger.error(
                "DomainAgentExecutor: domain=%s probe failed: %s",
                probe.domain_id,
                exc,
            )
            obs.emit_domain_status(
                event_bus,
                probe.probe_candidate_id,
                probe.domain_id,
                "failed",
                answer=f"error: {exc!s}",
            )
            return UnifiedEvidenceLedgerEntry(
                probe_id=new_probe_id(),
                question=probe.scoped_question,
                source_domain_id=probe.domain_id,
                result=f"Domain agent error: {exc!s}",
                sub_evidence=[],
                round_index=round_index,
                created_at=now_iso(),
            )
