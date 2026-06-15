"""Planner Consultant service (component 2)."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.models.planner_consultant import PlannerConsultantInput, PlannerConsultantOutput
from ic_agent.prompts import planner_consultant as prompts
from ic_agent.prompts.base import get_prompt_bundle
from ic_agent.services.llm_factory import get_chat_model

logger = logging.getLogger(__name__)

SERVICE_KEY = "planner_consultant"


class PlannerConsultantService:
    def __init__(self, chat_model: BaseChatModel | None = None):
        self._chat_model = chat_model or get_chat_model()

    def run(self, input_data: PlannerConsultantInput) -> PlannerConsultantOutput:
        bundle = get_prompt_bundle(prompts, SERVICE_KEY, input_data.domain_context)
        structured_model = self._chat_model.with_structured_output(PlannerConsultantOutput)

        messages = [
            SystemMessage(content=bundle.render()),
            HumanMessage(content=input_data.model_dump_json()),
        ]
        result = structured_model.invoke(messages)

        logger.info(
            "PlannerConsultant: objective=%r hypotheses=%d probe_candidates=%d",
            result.objective,
            len(result.hypotheses),
            len(result.probe_candidates),
        )
        return result
