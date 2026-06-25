"""Planner service (component 3).

Probe candidates are ordered by expected value (high first) and capped at
``max_probes_per_round`` -- deterministic, no LLM involved. The Planner
then makes one structured-output LLM call to translate each probe's
directional goal into concrete, retrieval-ready questions by selecting
KPIs from the question_format guide and forming questions the retrieval
service can parse. Each question becomes its own ``ToolCall``; the final
list is capped at ``max_probes_per_round``. The Planner Consultant never
sees KPIs, usecases, or retrieval mechanics.
"""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.domain import DomainConfig
from ic_agent.models.planner import (
    PlannerInput,
    PlannerOutput,
    PlannerUsecaseAssignments,
    ProbeUsecaseAssignment,
    ToolCall,
)
from ic_agent.models.planner_consultant import ProbeCandidate
from ic_agent.prompts import planner as prompts
from ic_agent.prompts.base import get_prompt_bundle
from ic_agent.services.llm_factory import get_chat_model
from ic_agent.utils.ids import new_probe_id

logger = logging.getLogger(__name__)

SERVICE_KEY = "planner"

_EXPECTED_VALUE_ORDER = {"high": 0, "medium": 1, "low": 2}


class PlannerService:
    def __init__(
        self,
        domain_config: DomainConfig,
        usecase_docs: dict[str, str],
        chat_model: BaseChatModel | None = None,
        probe_budget: ProbeBudgetConfig | None = None,
        schema_doc: str | None = None,
        question_format_doc: str | None = None,
    ):
        self._domain_config = domain_config
        self._usecase_docs = usecase_docs
        self._chat_model = chat_model or get_chat_model()
        self._probe_budget = probe_budget or ProbeBudgetConfig()
        self._schema_doc = schema_doc
        self._question_format_doc = question_format_doc

    def run(self, input_data: PlannerInput) -> PlannerOutput:
        candidates = sorted(
            input_data.consultant_plan.probe_candidates,
            key=lambda c: _EXPECTED_VALUE_ORDER.get(c.expected_value, 99),
        )
        candidates = candidates[: self._probe_budget.max_probes_per_round]

        hypothesis_ids = sorted({h.id for h in input_data.consultant_plan.hypotheses})
        asked_questions = {q.lower() for q in input_data.asked_questions}
        assignment_by_candidate = self._route_and_rewrite(candidates, input_data.asked_questions)
        default_usecase = next(iter(self._usecase_docs), "brand_guidance")

        tool_calls = []
        for candidate in candidates:
            assignment = assignment_by_candidate.get(candidate.id)
            if assignment is None:
                # LLM failed to produce an assignment — fall back to the raw goal
                questions = [candidate.goal]
            else:
                questions = [q.text for q in assignment.questions if q.keep]
                if not questions:
                    logger.debug(
                        "Planner: all questions dropped for candidate %r (%s), skipping",
                        candidate.id,
                        assignment.reason[:80] if assignment.reason else "no reason",
                    )
                    continue
            usecase = assignment.usecase if assignment else default_usecase
            for question in questions:
                if question.lower() in asked_questions:
                    logger.debug("Planner: skipping duplicate question: %r", question)
                    continue
                tool_calls.append(
                    ToolCall(
                        probe_id=new_probe_id(),
                        question=question,
                        related_hypothesis_ids=hypothesis_ids,
                        related_probe_candidate_id=candidate.id,
                        usecase=usecase,
                        reason=assignment.reason if assignment else "",
                    )
                )

        tool_calls = tool_calls[: self._probe_budget.max_probes_per_round]

        logger.info(
            "Planner: produced %d tool calls (capped at %d)",
            len(tool_calls),
            self._probe_budget.max_probes_per_round,
        )
        return PlannerOutput(tool_calls=tool_calls)

    def _route_and_rewrite(
        self, candidates: list[ProbeCandidate], asked_questions: list[str]
    ) -> dict[str, ProbeUsecaseAssignment]:
        if not candidates:
            return {}

        bundle = get_prompt_bundle(prompts, SERVICE_KEY, self._domain_config)
        structured_model = self._chat_model.with_structured_output(PlannerUsecaseAssignments)

        payload = {
            "probe_candidates": [c.model_dump() for c in candidates],
            "usecase_docs": self._usecase_docs,
        }
        if asked_questions:
            payload["asked_questions"] = asked_questions
        if self._schema_doc:
            payload["schema"] = self._schema_doc
        if self._question_format_doc:
            payload["question_format"] = self._question_format_doc
        messages = [
            SystemMessage(content=bundle.render()),
            HumanMessage(content=json.dumps(payload)),
        ]
        result = structured_model.invoke(messages)
        return {a.probe_candidate_id: a for a in result.assignments}
