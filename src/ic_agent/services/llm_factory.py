"""Shared OpenAI chat model construction.

Centralizing this means services can accept an injected
``BaseChatModel`` (e.g. a fake/stub in tests) without each one needing to
know how to build a real client.
"""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ic_agent.config.settings import Settings, get_settings
from ic_agent.utils.ssl_setup import ensure_system_truststore


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """Return a deterministic (temperature=0) ChatOpenAI instance.

    If a LiteLLM proxy is configured (``AZURE_OPENAI_ENDPOINT_LITELLM`` /
    ``AZURE_OPENAI_API_KEY_LITELLM``), requests are routed through it via
    its OpenAI-compatible API. Otherwise falls back to talking to OpenAI
    directly using ``OPENAI_API_KEY``.
    """
    settings = settings or get_settings()
    if settings.litellm_base_url and settings.litellm_api_key:
        ensure_system_truststore()
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.litellm_api_key,
            base_url=settings.litellm_base_url,
            temperature=0,
        )

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
