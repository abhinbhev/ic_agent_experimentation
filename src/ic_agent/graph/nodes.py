"""LangGraph node factories.

Each ``make_*_node`` function closes over a service instance and returns
a node callable ``(AgentState) -> dict`` that converts state into the
service's pydantic ``*Input`` model, calls the service, and returns a
partial-state update built from the validated ``*Output`` model.
"""

import logging
from typing import Callable

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_consultant import DecisionConsultantInput
from ic_agent.models.decision_engine import DecisionEngineInput
from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.planner import PlannerInput
from ic_agent.models.planner_consultant import PlannerConsultantInput
from ic_agent.models.similar_plan import SimilarPlanQuery
from ic_agent.models.state import AgentState
from ic_agent.models.synthesizer import SynthesizerInput
from ic_agent.services.decision_consultant_service import DecisionConsultantService
from ic_agent.services.decision_engine_service import DecisionEngineService
from ic_agent.services.planner_consultant_service import PlannerConsultantService
from ic_agent.services.planner_service import PlannerService
from ic_agent.services.retrieval_service import RetrievalService
from ic_agent.services.similar_plan_service import SimilarPlanService
from ic_agent.services.synthesizer_service import SynthesizerService
from ic_agent.utils.timing import now_iso

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], dict]


def make_similar_plan_node(service: SimilarPlanService) -> NodeFn:
    def node(state: AgentState) -> dict:
        query = SimilarPlanQuery(user_query=state["query"], domain_context=state["domain_config"])
        result = service.search(query)
        return {"similar_patterns": result.matched_patterns}

    return node


def make_planner_consultant_node(service: PlannerConsultantService) -> NodeFn:
    def node(state: AgentState) -> dict:
        decision_consultant_output = state.get("decision_consultant_output")
        remaining_gaps = (
            [g.description for g in decision_consultant_output.remaining_gaps]
            if decision_consultant_output
            else []
        )

        input_data = PlannerConsultantInput(
            query=state["query"],
            domain_context=state["domain_config"],
            similar_patterns=state.get("similar_patterns", []),
            evidence_ledger=state.get("evidence_ledger", []),
            remaining_gaps=remaining_gaps,
            recommended_next_gap=state.get("recommended_next_gap"),
        )
        output = service.run(input_data)
        return {"consultant_plan": output}

    return node


def make_planner_node(service: PlannerService) -> NodeFn:
    def node(state: AgentState) -> dict:
        asked = [e.question for e in state.get("evidence_ledger", [])]
        output = service.run(
            PlannerInput(consultant_plan=state["consultant_plan"], asked_questions=asked)
        )
        return {"tool_calls": output.tool_calls}

    return node


def make_execution_node(service: RetrievalService) -> NodeFn:
    def node(state: AgentState) -> dict:
        round_index = state.get("rounds_completed", 0)
        new_entries = [
            EvidenceLedgerEntry(
                probe_id=tc.probe_id,
                question=tc.question,
                result=service.query(tc.question, tc.usecase),
                relevance_score=0.0,
                gap_closed="",
                created_at=now_iso(),
                round_index=round_index,
            )
            for tc in state.get("tool_calls", [])
        ]

        updated_ledger = state.get("evidence_ledger", []) + new_entries
        return {
            "evidence_ledger": updated_ledger,
            "probes_completed_this_round": len(new_entries),
            "total_probes_completed": state.get("total_probes_completed", 0) + len(new_entries),
        }

    return node


def make_decision_consultant_node(service: DecisionConsultantService) -> NodeFn:
    def node(state: AgentState) -> dict:
        output = service.run(
            DecisionConsultantInput(query=state["query"], ledger=state.get("evidence_ledger", []))
        )
        return {"decision_consultant_output": output, "confidence": output.confidence}

    return node


def make_decision_engine_node(service: DecisionEngineService, probe_budget: ProbeBudgetConfig) -> NodeFn:
    def node(state: AgentState) -> dict:
        output = service.run(
            DecisionEngineInput(
                ledger=state.get("evidence_ledger", []),
                decision_consultant_output=state["decision_consultant_output"],
                rounds_completed=state.get("rounds_completed", 0),
                probes_completed_this_round=state.get("probes_completed_this_round", 0),
                total_probes_completed=state.get("total_probes_completed", 0),
                probe_budget=probe_budget,
            )
        )
        return {
            "decision_engine_output": output,
            "rounds_completed": state.get("rounds_completed", 0) + 1,
            "remaining_gaps": [g.description for g in state["decision_consultant_output"].remaining_gaps],
            "recommended_next_gap": output.recommended_next_gap,
            "stop_reason": output.stop_reason,
        }

    return node


def make_synthesis_node(service: SynthesizerService) -> NodeFn:
    def node(state: AgentState) -> dict:
        output = service.run(
            SynthesizerInput(
                query=state["query"],
                ledger=state.get("evidence_ledger", []),
                decision_consultant_output=state.get("decision_consultant_output"),
                stop_reason=state.get("stop_reason", "unknown"),
            )
        )
        return {"final_answer": output}

    return node
