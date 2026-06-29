"""Unified Decision Consultant service."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from unified_domain.models.decision_consultant import (
    UnifiedDecisionConsultantInput,
    UnifiedDecisionConsultantOutput,
)
from unified_domain.prompts.decision_consultant import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class UnifiedDecisionConsultantService:
    def __init__(self, chat_model: BaseChatModel):
        self._chat_model = chat_model

    def run(self, input_data: UnifiedDecisionConsultantInput) -> UnifiedDecisionConsultantOutput:
        structured_model = self._chat_model.with_structured_output(UnifiedDecisionConsultantOutput)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=input_data.model_dump_json()),
        ]
        result = structured_model.invoke(messages)

        unresolved = sum(
            1 for g in result.remaining_gaps if g.category in {"open", "partial", "conflicting"}
        )
        logger.info(
            "UnifiedDecisionConsultant: confidence=%.2f, %d gaps (%d unresolved)",
            result.confidence,
            len(result.remaining_gaps),
            unresolved,
        )
        return result
