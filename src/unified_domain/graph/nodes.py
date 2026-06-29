"""LangGraph node factories for the unified (super-agent) pipeline.

Each ``make_*_node`` function closes over a service instance and returns
a node callable ``(UnifiedAgentState) -> dict`` that converts state into
the service's pydantic input model, calls the service, and returns a
partial-state update.
"""

import logging
from typing import Callable

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.similar_plan import SimilarPlanQuery
from ic_agent.services.similar_plan_service import SimilarPlanService
from unified_domain.models.decision_consultant import (
    UnifiedDecisionConsultantInput,
)
from unified_domain.models.domain_router import DomainRouterInput
from unified_domain.models.planner_consultant import (
    UnifiedPlannerConsultantInput,
)
from unified_domain.models.state import UnifiedAgentState
from unified_domain.observability import instrumentation as obs
from unified_domain.services.decision_consultant_service import (
    UnifiedDecisionConsultantService,
)
from unified_domain.services.decision_engine_service import (
    UnifiedDecisionEngineInput,
    UnifiedDecisionEngineService,
)
from unified_domain.services.domain_agent_executor import DomainAgentExecutor
from unified_domain.services.domain_router_service import DomainRouterService
from unified_domain.services.planner_consultant_service import (
    UnifiedPlannerConsultantService,
)
from unified_domain.services.synthesizer_service import (
    UnifiedSynthesizerInput,
    UnifiedSynthesizerService,
)

logger = logging.getLogger(__name__)

NodeFn = Callable[[UnifiedAgentState], dict]


def make_similar_plan_node(service: SimilarPlanService) -> NodeFn:
    """Search across all domain corpora for investigation patterns."""

    def node(state: UnifiedAgentState) -> dict:
        bus = state.get("event_bus")
        obs.emit_root(bus, state["query"])

        domain_context = state["available_domains"][0] if state.get("available_domains") else None
        query = SimilarPlanQuery(user_query=state["query"], domain_context=domain_context)
        result = service.search(query)
        logger.info("UnifiedSimilarPlan: matched %d patterns", len(result.matched_patterns))
        return {"similar_patterns": result.matched_patterns}

    return node


def make_planner_consultant_node(
    service: UnifiedPlannerConsultantService,
) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        dc_output = state.get("decision_consultant_output")
        remaining_gaps = [g.description for g in dc_output.remaining_gaps] if dc_output else []

        input_data = UnifiedPlannerConsultantInput(
            query=state["query"],
            available_domains=state.get("available_domains", []),
            domain_knowledge_doc=state.get("domain_knowledge_doc", ""),
            similar_patterns=state.get("similar_patterns", []),
            evidence_ledger=state.get("evidence_ledger", []),
            remaining_gaps=remaining_gaps,
            recommended_next_gap=state.get("recommended_next_gap"),
        )
        output = service.run(input_data)
        logger.info(
            "UnifiedPlannerConsultant: %d hypotheses, %d probes",
            len(output.hypotheses),
            len(output.probe_candidates),
        )

        # Observability: open a new super-round and emit its super-probes
        bus = state.get("event_bus")
        round_idx_1based = state.get("rounds_completed", 0) + 1
        sublabel = (
            f"Continued from prior round (gap: {state.get('recommended_next_gap')})"
            if dc_output
            else "Initial investigation"
        )
        obs.emit_super_round_start(bus, round_idx_1based, sublabel=sublabel)
        obs.emit_super_probes(bus, round_idx_1based, output)

        return {"consultant_plan": output}

    return node


def make_domain_router_node(service: DomainRouterService) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        asked = [e.question for e in state.get("evidence_ledger", [])]
        input_data = DomainRouterInput(
            consultant_plan=state["consultant_plan"],
            available_domains=state.get("available_domains", []),
            asked_questions=asked,
        )
        output = service.run(input_data)
        logger.info("UnifiedDomainRouter: %d assignments", len(output.assignments))

        # Observability: emit domain nodes for each assigned probe + mark
        # any super-probe with at least one assignment as "running".
        bus = state.get("event_bus")
        obs.emit_domain_assignments(bus, output.assignments)
        seen_super_probes = set()
        for a in output.assignments:
            for probe in a.probes:
                if probe.probe_candidate_id not in seen_super_probes:
                    obs.emit_super_probe_status(bus, probe.probe_candidate_id, "running")
                    seen_super_probes.add(probe.probe_candidate_id)

        return {"domain_assignments": output.assignments}

    return node


def make_domain_execution_node(executor: DomainAgentExecutor) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        round_index = state.get("rounds_completed", 0)
        assignments = state.get("domain_assignments", [])
        bus = state.get("event_bus")

        new_entries = executor.execute_sync(assignments, round_index, event_bus=bus)

        updated_ledger = state.get("evidence_ledger", []) + new_entries
        logger.info(
            "UnifiedExecution: %d new entries, %d total in ledger",
            len(new_entries),
            len(updated_ledger),
        )

        # Once execution returns, mark each super-probe answered if all its
        # domain assignments are done. Simpler: just mark them all answered;
        # if a future round revisits the same probe id (it shouldn't — IDs
        # are unique per consultant call), a new event will overwrite.
        for a in assignments:
            for probe in a.probes:
                obs.emit_super_probe_status(bus, probe.probe_candidate_id, "answered")

        return {
            "evidence_ledger": updated_ledger,
            "probes_completed_this_round": len(new_entries),
            "total_probes_completed": state.get("total_probes_completed", 0) + len(new_entries),
        }

    return node


def make_decision_consultant_node(
    service: UnifiedDecisionConsultantService,
) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        output = service.run(
            UnifiedDecisionConsultantInput(
                query=state["query"],
                ledger=state.get("evidence_ledger", []),
            )
        )
        logger.info("UnifiedDecisionConsultant: confidence=%.2f", output.confidence)
        return {"decision_consultant_output": output, "confidence": output.confidence}

    return node


def make_decision_engine_node(
    service: UnifiedDecisionEngineService, probe_budget: ProbeBudgetConfig
) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        output = service.run(
            UnifiedDecisionEngineInput(
                ledger=state.get("evidence_ledger", []),
                decision_consultant_output=state["decision_consultant_output"],
                rounds_completed=state.get("rounds_completed", 0),
                probes_completed_this_round=state.get("probes_completed_this_round", 0),
                total_probes_completed=state.get("total_probes_completed", 0),
                probe_budget=probe_budget,
            )
        )
        logger.info(
            "UnifiedDecisionEngine: continue=%s stop_reason=%s IVF=%.3f",
            output.continue_,
            output.stop_reason,
            output.expected_incremental_value,
        )

        # Attach stop-condition metrics to the super-round, then close it
        # so the next planner_consultant run opens a fresh SR{n+1}.
        bus = state.get("event_bus")
        round_idx_1based = state.get("rounds_completed", 0) + 1
        obs.emit_round_metrics(
            bus,
            obs.super_round_id(round_idx_1based),
            "root",
            "super-round",
            round_idx_1based,
            output,
        )
        obs.emit_super_round_done(bus, round_idx_1based)

        return {
            "decision_engine_output": output,
            "rounds_completed": state.get("rounds_completed", 0) + 1,
            "remaining_gaps": [
                g.description for g in state["decision_consultant_output"].remaining_gaps
            ],
            "recommended_next_gap": output.recommended_next_gap,
            "stop_reason": output.stop_reason,
        }

    return node


def make_synthesis_node(service: UnifiedSynthesizerService) -> NodeFn:
    def node(state: UnifiedAgentState) -> dict:
        output = service.run(
            UnifiedSynthesizerInput(
                query=state["query"],
                ledger=state.get("evidence_ledger", []),
                decision_consultant_output=state.get("decision_consultant_output"),
                stop_reason=state.get("stop_reason", "unknown"),
                domain_knowledge_doc=state.get("domain_knowledge_doc", ""),
            )
        )
        logger.info("UnifiedSynthesizer: confidence=%.2f", output.confidence)

        bus = state.get("event_bus")
        obs.emit_root_answered(bus, output.markdown)

        return {"final_answer": output}

    return node
