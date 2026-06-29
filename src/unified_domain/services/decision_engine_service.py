"""Unified Decision Engine service.

Delegates the deterministic IVF scoring to the existing single-agent
``DecisionEngineService`` by converting unified models to single-agent
format. The gap-recommendation LLM call uses the unified prompt.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from pydantic import BaseModel, Field

from ic_agent.config.probe_budget import IncrementalValueWeights, ProbeBudgetConfig
from ic_agent.models.decision_consultant import (
    DecisionConsultantOutput,
    RemainingGap,
)
from ic_agent.models.decision_engine import (
    DecisionEngineInput,
    DecisionEngineOutput,
    GapRecommendation,
    IncrementalValueBreakdown,
)
from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.planner_consultant import Hypothesis
from unified_domain.models.decision_consultant import UnifiedDecisionConsultantOutput
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.prompts.decision_engine import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_UNRESOLVED_GAP_CATEGORIES = {"open", "partial", "conflicting"}
_ASSUMED_MAX_NEW_HYPOTHESES = 3


class UnifiedDecisionEngineInput(BaseModel):
    """Input for the unified decision engine."""

    ledger: list[UnifiedEvidenceLedgerEntry] = Field(default_factory=list)
    decision_consultant_output: UnifiedDecisionConsultantOutput
    rounds_completed: int = Field(ge=0)
    probes_completed_this_round: int = Field(ge=0)
    total_probes_completed: int = Field(ge=0)
    probe_budget: ProbeBudgetConfig = Field(default_factory=ProbeBudgetConfig)


def _to_single_agent_dc_output(
    unified: UnifiedDecisionConsultantOutput,
) -> DecisionConsultantOutput:
    """Convert unified decision consultant output to single-agent format."""
    return DecisionConsultantOutput(
        relevant_probes=unified.relevant_probes,
        irrelevant_probes=unified.irrelevant_probes,
        remaining_gaps=[
            RemainingGap(description=g.description, category=g.category)
            for g in unified.remaining_gaps
        ],
        new_hypotheses=[
            Hypothesis(id=h.id, description=h.description, status=h.status)
            for h in unified.new_hypotheses
        ],
        confidence=unified.confidence,
    )


def _to_single_agent_ledger(
    unified_ledger: list[UnifiedEvidenceLedgerEntry],
) -> list[EvidenceLedgerEntry]:
    """Convert unified ledger entries to single-agent format."""
    return [
        EvidenceLedgerEntry(
            probe_id=e.probe_id,
            question=e.question,
            result=e.result,
            relevance_score=e.relevance_score,
            gap_closed=e.gap_closed,
            created_at=e.created_at,
            round_index=e.round_index,
        )
        for e in unified_ledger
    ]


class UnifiedDecisionEngineService:
    def __init__(
        self,
        chat_model: BaseChatModel,
        weights: IncrementalValueWeights | None = None,
    ):
        self._chat_model = chat_model
        self._weights = weights or IncrementalValueWeights()

    def run(self, input_data: UnifiedDecisionEngineInput) -> DecisionEngineOutput:
        sa_dc_output = _to_single_agent_dc_output(input_data.decision_consultant_output)
        sa_ledger = _to_single_agent_ledger(input_data.ledger)

        sa_input = DecisionEngineInput(
            ledger=sa_ledger,
            decision_consultant_output=sa_dc_output,
            rounds_completed=input_data.rounds_completed,
            probes_completed_this_round=input_data.probes_completed_this_round,
            total_probes_completed=input_data.total_probes_completed,
            probe_budget=input_data.probe_budget,
        )

        breakdown = self._score_breakdown(sa_input)
        stop_reason, continue_ = self._stop_condition(sa_input, breakdown)

        if stop_reason in (
            "max_rounds_reached",
            "max_total_probes_reached",
            "no_progress_this_round",
        ):
            reason_text = {
                "max_rounds_reached": "Stopping: maximum rounds reached.",
                "max_total_probes_reached": ("Stopping: maximum total probes reached."),
                "no_progress_this_round": (
                    "Stopping: no new evidence was gathered this round — "
                    "the Planner either produced no questions or every "
                    "probe was irrelevant. Continuing would not make "
                    "progress on the remaining gaps."
                ),
            }[stop_reason]
            recommendation = GapRecommendation(
                recommended_next_gap=None,
                reason=reason_text,
            )
        elif stop_reason == "all_major_gaps_closed":
            recommendation = GapRecommendation(
                recommended_next_gap=None,
                reason=("Stopping: no open, partial or conflicting gaps remain."),
            )
        else:
            recommendation = self._recommend_next_gap(input_data)

        output = DecisionEngineOutput(
            **{"continue": continue_},
            expected_incremental_value=breakdown.weighted_total,
            recommended_next_gap=recommendation.recommended_next_gap,
            reason=recommendation.reason,
            stop_reason=stop_reason,
            value_breakdown=breakdown,
        )

        logger.info(
            "DecisionEngine: continue=%s stop_reason=%s " "expected_incremental_value=%.3f",
            output.continue_,
            output.stop_reason,
            output.expected_incremental_value,
        )
        return output

    # ------------------------------------------------------------------
    # Deterministic IVF scoring (copied from single-agent to avoid
    # tight coupling on DomainConfig, which unified doesn't use).
    # ------------------------------------------------------------------

    def _score_breakdown(self, input_data: DecisionEngineInput) -> IncrementalValueBreakdown:
        consultant = input_data.decision_consultant_output

        evidence_coverage = len(consultant.relevant_probes) / max(
            input_data.total_probes_completed, 1
        )
        confidence = consultant.confidence

        all_gaps = consultant.remaining_gaps
        unresolved = [g for g in all_gaps if g.category in _UNRESOLVED_GAP_CATEGORIES]
        remaining_gaps_score = len(unresolved) / max(len(all_gaps), 1)

        alternative_hypotheses_score = min(
            len(consultant.new_hypotheses) / _ASSUMED_MAX_NEW_HYPOTHESES, 1.0
        )

        probe_cost_score = max(
            0.0,
            1.0 - (input_data.total_probes_completed / input_data.probe_budget.max_total_probes),
        )

        w = self._weights
        weighted_total = (
            w.evidence_coverage * evidence_coverage
            + w.confidence * confidence
            + w.remaining_gaps * remaining_gaps_score
            + w.alternative_hypotheses * alternative_hypotheses_score
            + w.probe_cost * probe_cost_score
        )

        return IncrementalValueBreakdown(
            evidence_coverage=evidence_coverage,
            confidence=confidence,
            remaining_gaps_score=remaining_gaps_score,
            alternative_hypotheses_score=alternative_hypotheses_score,
            probe_cost_score=probe_cost_score,
            weighted_total=weighted_total,
        )

    def _stop_condition(
        self,
        input_data: DecisionEngineInput,
        breakdown: IncrementalValueBreakdown,
    ) -> tuple[str, bool]:
        budget = input_data.probe_budget
        consultant = input_data.decision_consultant_output

        if input_data.rounds_completed >= budget.max_rounds:
            return "max_rounds_reached", False

        if input_data.total_probes_completed >= budget.max_total_probes:
            return "max_total_probes_reached", False

        if not any(g.category in _UNRESOLVED_GAP_CATEGORIES for g in consultant.remaining_gaps):
            return "all_major_gaps_closed", False

        if input_data.probes_completed_this_round == 0:
            return "no_progress_this_round", False

        irrelevant_ids = set(consultant.irrelevant_probes)
        current_round_ids = {
            e.probe_id for e in input_data.ledger if e.round_index == input_data.rounds_completed
        }
        if current_round_ids and current_round_ids.issubset(irrelevant_ids):
            return "no_progress_this_round", False

        if breakdown.weighted_total < self._weights.stop_threshold:
            return "incremental_value_below_threshold", False

        return "continue", True

    def _recommend_next_gap(self, input_data: UnifiedDecisionEngineInput) -> GapRecommendation:
        structured_model = self._chat_model.with_structured_output(GapRecommendation)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=input_data.model_dump_json()),
        ]
        return structured_model.invoke(messages)
