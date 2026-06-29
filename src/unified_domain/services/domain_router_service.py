"""Domain Router service — assigns probe candidates to sub-domains.

Follows the same structural pattern as
``ic_agent.services.planner_service.PlannerService``:
probe candidates are sorted by expected value (high first), capped at
``max_probes_per_round``, then a single structured-output LLM call
produces domain assignments.  A deterministic dedup backstop drops any
``scoped_question`` already in ``asked_questions``.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.config.probe_budget import ProbeBudgetConfig
from unified_domain.models.domain_router import (
    DomainAssignment,
    DomainRouterInput,
    DomainRouterOutput,
)
from unified_domain.models.planner_consultant import UnifiedPlannerConsultantOutput  # noqa: F401 — resolve forward ref
from unified_domain.prompts.domain_router import SYSTEM_PROMPT

DomainRouterInput.model_rebuild()

logger = logging.getLogger(__name__)

_EXPECTED_VALUE_ORDER = {"high": 0, "medium": 1, "low": 2}


class DomainRouterService:
    def __init__(self, chat_model, probe_budget: ProbeBudgetConfig | None = None):
        self._chat_model = chat_model
        self._probe_budget = probe_budget or ProbeBudgetConfig()

    def run(self, input_data: DomainRouterInput) -> DomainRouterOutput:
        candidates = sorted(
            input_data.consultant_plan.probe_candidates,
            key=lambda c: _EXPECTED_VALUE_ORDER.get(c.expected_value, 99),
        )
        candidates = candidates[: self._probe_budget.max_probes_per_round]

        if not candidates:
            logger.warning("DomainRouter: no probe candidates to route")
            return DomainRouterOutput(assignments=[])

        asked_lower = {q.lower() for q in input_data.asked_questions}

        # -- LLM call --
        payload = {
            "probe_candidates": [c.model_dump() for c in candidates],
            "available_domains": [
                {
                    "domain_id": d.domain_id,
                    "display_name": d.display_name,
                    "datasets": [ds.model_dump() for ds in d.datasets],
                }
                for d in input_data.available_domains
            ],
        }
        if input_data.asked_questions:
            payload["asked_questions"] = input_data.asked_questions

        structured_model = self._chat_model.with_structured_output(DomainRouterOutput)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload)),
        ]
        result: DomainRouterOutput = structured_model.invoke(messages)

        if not result.assignments:
            logger.warning("DomainRouter: LLM returned empty assignments")
            return DomainRouterOutput(assignments=[])

        # -- deterministic dedup backstop --
        cleaned_assignments: list[DomainAssignment] = []
        total_probes = 0
        cap = self._probe_budget.max_probes_per_round

        for assignment in result.assignments:
            kept_probes = []
            for probe in assignment.probes:
                if probe.scoped_question.lower() in asked_lower:
                    logger.debug(
                        "DomainRouter: skipping duplicate question: %r",
                        probe.scoped_question,
                    )
                    continue
                if total_probes >= cap:
                    break
                kept_probes.append(probe)
                total_probes += 1
            if kept_probes:
                cleaned_assignments.append(
                    DomainAssignment(
                        domain_id=assignment.domain_id,
                        domain_display_name=assignment.domain_display_name,
                        probes=kept_probes,
                    )
                )
            if total_probes >= cap:
                break

        unique_domains = {a.domain_id for a in cleaned_assignments}
        logger.info(
            "DomainRouter: produced %d assignments across %d domains (capped at %d)",
            total_probes,
            len(unique_domains),
            cap,
        )
        for a in cleaned_assignments:
            logger.debug(
                "DomainRouter: domain %r — %d probes",
                a.domain_id,
                len(a.probes),
            )

        return DomainRouterOutput(assignments=cleaned_assignments)
