"""Decision Engine service (component 7).

Determines whether another probe cycle is worthwhile. The continue/stop
decision and the Incremental Value Framework score are computed
deterministically in Python (reproducible, testable without a model). A
small LLM call is used only to produce a qualitative
``recommended_next_gap`` + ``reason`` when the engine decides to continue
or when the marginal value is too low -- not for budget-exhaustion stops,
which already have an objective reason.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.config.probe_budget import IncrementalValueWeights
from ic_agent.models.decision_engine import (
    DecisionEngineInput,
    DecisionEngineOutput,
    GapRecommendation,
    IncrementalValueBreakdown,
)
from ic_agent.models.domain import DomainConfig
from ic_agent.prompts import decision_engine as prompts
from ic_agent.prompts.base import get_prompt_bundle
from ic_agent.services.llm_factory import get_chat_model

logger = logging.getLogger(__name__)

SERVICE_KEY = "decision_engine"

_UNRESOLVED_GAP_CATEGORIES = {"open", "partial", "conflicting"}

# Assumed soft ceiling on new hypotheses per round, used to normalize the
# "alternative hypotheses" sub-score into [0, 1].
_ASSUMED_MAX_NEW_HYPOTHESES = 3


class DecisionEngineService:
    def __init__(
        self,
        domain_config: DomainConfig,
        chat_model: BaseChatModel | None = None,
        weights: IncrementalValueWeights | None = None,
    ):
        self._domain_config = domain_config
        self._chat_model = chat_model or get_chat_model()
        self._weights = weights or IncrementalValueWeights()

    def run(self, input_data: DecisionEngineInput) -> DecisionEngineOutput:
        breakdown = self._score_breakdown(input_data)

        stop_reason, continue_ = self._stop_condition(input_data, breakdown)

        if stop_reason in (
            "max_rounds_reached",
            "max_total_probes_reached",
            "no_progress_this_round",
        ):
            reason_text = {
                "max_rounds_reached": "Stopping: maximum rounds reached.",
                "max_total_probes_reached": "Stopping: maximum total probes reached.",
                "no_progress_this_round": (
                    "Stopping: no new evidence was gathered this round — "
                    "the Planner either produced no questions or every probe was irrelevant. "
                    "Continuing would not make progress on the remaining gaps."
                ),
            }[stop_reason]
            recommendation = GapRecommendation(
                recommended_next_gap=None,
                reason=reason_text,
            )
        elif stop_reason == "all_major_gaps_closed":
            recommendation = GapRecommendation(
                recommended_next_gap=None,
                reason="Stopping: no open, partial or conflicting gaps remain.",
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
            "DecisionEngine: continue=%s stop_reason=%s expected_incremental_value=%.3f",
            output.continue_,
            output.stop_reason,
            output.expected_incremental_value,
        )
        return output

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
        self, input_data: DecisionEngineInput, breakdown: IncrementalValueBreakdown
    ) -> tuple[str, bool]:
        budget = input_data.probe_budget
        consultant = input_data.decision_consultant_output

        if input_data.rounds_completed >= budget.max_rounds:
            return "max_rounds_reached", False

        if input_data.total_probes_completed >= budget.max_total_probes:
            return "max_total_probes_reached", False

        if not any(g.category in _UNRESOLVED_GAP_CATEGORIES for g in consultant.remaining_gaps):
            return "all_major_gaps_closed", False

        # Stall detection: stop if the Planner produced nothing to execute, or if
        # everything it did execute was irrelevant — either way, continuing won't help.
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

    def _recommend_next_gap(self, input_data: DecisionEngineInput) -> GapRecommendation:
        bundle = get_prompt_bundle(prompts, SERVICE_KEY, self._domain_config)
        structured_model = self._chat_model.with_structured_output(GapRecommendation)

        messages = [
            SystemMessage(content=bundle.render()),
            HumanMessage(content=input_data.model_dump_json()),
        ]
        return structured_model.invoke(messages)
