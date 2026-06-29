"""Unified Planner Consultant service."""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from unified_domain.models.planner_consultant import (
    UnifiedPlannerConsultantInput,
    UnifiedPlannerConsultantOutput,
)
from unified_domain.prompts.planner_consultant import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class UnifiedPlannerConsultantService:
    def __init__(self, chat_model: BaseChatModel):
        self._chat_model = chat_model

    def run(self, input_data: UnifiedPlannerConsultantInput) -> UnifiedPlannerConsultantOutput:
        structured_model = self._chat_model.with_structured_output(UnifiedPlannerConsultantOutput)

        # Serialize available_domains as lightweight dicts with only the
        # fields the LLM needs (domain_id, display_name, datasets).
        domain_dicts = []
        for d in input_data.available_domains:
            domain_dicts.append(
                {
                    "domain_id": d.domain_id,
                    "display_name": d.display_name,
                    "datasets": [
                        {"name": ds.name, "description": ds.description}
                        for ds in (d.datasets or [])
                    ],
                }
            )

        payload = {
            "query": input_data.query,
            "domain_knowledge_doc": input_data.domain_knowledge_doc,
            "available_domains": domain_dicts,
            "similar_patterns": [p.model_dump() for p in input_data.similar_patterns],
            "evidence_ledger": [e.model_dump() for e in input_data.evidence_ledger],
            "remaining_gaps": input_data.remaining_gaps,
            "recommended_next_gap": input_data.recommended_next_gap,
        }

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload)),
        ]
        result = structured_model.invoke(messages)

        logger.info(
            "UnifiedPlannerConsultant: produced %d hypotheses, %d probe candidates",
            len(result.hypotheses),
            len(result.probe_candidates),
        )
        return result
