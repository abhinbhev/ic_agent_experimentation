"""Integration test that exercises a real chat completion via ``with_structured_output``.

Skipped unless either ``OPENAI_API_KEY`` or a LiteLLM proxy
(``AZURE_OPENAI_ENDPOINT_LITELLM`` / ``AZURE_OPENAI_API_KEY_LITELLM``) is
configured in the environment / ``.env`` file.
"""

import pytest

from ic_agent.config.settings import get_settings
from ic_agent.models.planner_consultant import PlannerConsultantInput, PlannerConsultantOutput
from ic_agent.services.llm_factory import get_chat_model
from ic_agent.services.planner_consultant_service import PlannerConsultantService

_settings = get_settings()
_has_llm_credentials = bool(_settings.openai_api_key) or bool(
    _settings.litellm_base_url and _settings.litellm_api_key
)

pytestmark = pytest.mark.skipif(
    not _has_llm_credentials, reason="requires OPENAI_API_KEY or LiteLLM credentials"
)


def test_planner_consultant_service_real_llm(sample_domain_config):
    service = PlannerConsultantService(get_chat_model())

    result = service.run(
        PlannerConsultantInput(
            query="Why did revenue decline in East China during Q1?",
            domain_context=sample_domain_config,
        )
    )

    assert isinstance(result, PlannerConsultantOutput)
    assert result.objective
    assert result.success_criteria
