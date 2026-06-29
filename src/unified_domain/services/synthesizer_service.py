"""Unified Final Answer Synthesizer service."""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ic_agent.models.synthesizer import SynthesizerOutput
from unified_domain.models.decision_consultant import UnifiedDecisionConsultantOutput
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.prompts.synthesizer import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class UnifiedSynthesizerInput(BaseModel):
    """Input for the unified synthesizer."""

    query: str
    ledger: list[UnifiedEvidenceLedgerEntry] = Field(default_factory=list)
    decision_consultant_output: UnifiedDecisionConsultantOutput | None = None
    stop_reason: str
    domain_knowledge_doc: str = ""


class UnifiedSynthesizerService:
    def __init__(
        self,
        chat_model: BaseChatModel,
        domain_knowledge_doc: str = "",
    ):
        self._chat_model = chat_model
        self._domain_knowledge_doc = domain_knowledge_doc

    def run(self, input_data: UnifiedSynthesizerInput) -> SynthesizerOutput:
        structured_model = self._chat_model.with_structured_output(SynthesizerOutput)

        payload = json.loads(input_data.model_dump_json())
        # Merge instance-level domain_knowledge_doc if input didn't provide one
        if not input_data.domain_knowledge_doc and self._domain_knowledge_doc:
            payload["domain_knowledge_doc"] = self._domain_knowledge_doc

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload)),
        ]
        result = structured_model.invoke(messages)

        logger.info(
            "UnifiedSynthesizer: confidence=%.2f",
            result.confidence,
        )
        return result
