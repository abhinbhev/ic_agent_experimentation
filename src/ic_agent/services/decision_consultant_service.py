"""Decision Consultant service (component 6)."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.models.decision_consultant import DecisionConsultantInput, DecisionConsultantOutput
from ic_agent.models.domain import DomainConfig
from ic_agent.prompts import decision_consultant as prompts
from ic_agent.prompts.base import get_prompt_bundle
from ic_agent.services.llm_factory import get_chat_model

logger = logging.getLogger(__name__)

SERVICE_KEY = "decision_consultant"


class DecisionConsultantService:
    def __init__(self, domain_config: DomainConfig, chat_model: BaseChatModel | None = None):
        self._domain_config = domain_config
        self._chat_model = chat_model or get_chat_model()

    def run(self, input_data: DecisionConsultantInput) -> DecisionConsultantOutput:
        bundle = get_prompt_bundle(prompts, SERVICE_KEY, self._domain_config)
        structured_model = self._chat_model.with_structured_output(DecisionConsultantOutput)

        messages = [
            SystemMessage(content=bundle.render()),
            HumanMessage(content=input_data.model_dump_json()),
        ]
        result = structured_model.invoke(messages)

        logger.info(
            "DecisionConsultant: confidence=%.2f remaining_gaps=%d new_hypotheses=%d",
            result.confidence,
            len(result.remaining_gaps),
            len(result.new_hypotheses),
        )
        return result
