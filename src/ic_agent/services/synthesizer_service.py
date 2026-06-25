"""Final Answer Synthesizer service (component 8)."""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ic_agent.models.domain import DomainConfig
from ic_agent.models.synthesizer import SynthesizerInput, SynthesizerOutput
from ic_agent.prompts import synthesizer as prompts
from ic_agent.prompts.base import get_prompt_bundle
from ic_agent.services.llm_factory import get_chat_model

logger = logging.getLogger(__name__)

SERVICE_KEY = "synthesizer"


class SynthesizerService:
    def __init__(
        self,
        domain_config: DomainConfig,
        chat_model: BaseChatModel | None = None,
        usecase_docs: dict[str, str] | None = None,
        schema_doc: str | None = None,
    ):
        self._domain_config = domain_config
        self._chat_model = chat_model or get_chat_model()
        self._usecase_docs = usecase_docs or {}
        self._schema_doc = schema_doc

    def run(self, input_data: SynthesizerInput) -> SynthesizerOutput:
        bundle = get_prompt_bundle(prompts, SERVICE_KEY, self._domain_config)
        structured_model = self._chat_model.with_structured_output(SynthesizerOutput)

        payload = json.loads(input_data.model_dump_json())
        if self._usecase_docs:
            payload["usecase_docs"] = self._usecase_docs
        if self._schema_doc:
            payload["schema_doc"] = self._schema_doc

        messages = [
            SystemMessage(content=bundle.render()),
            HumanMessage(content=json.dumps(payload)),
        ]
        result = structured_model.invoke(messages)

        logger.info(
            "Synthesizer: confidence=%.2f markdown_length=%d",
            result.confidence,
            len(result.markdown),
        )
        return result
