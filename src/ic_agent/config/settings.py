"""Environment-driven settings.

All environment variables are read here (and nowhere else), keeping
config concerns separate from business logic. Values can be overridden
via a ``.env`` file (see ``.env.example``).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.4", validation_alias="IC_AGENT_OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="IC_AGENT_EMBEDDING_MODEL"
    )

    # Optional LiteLLM proxy (OpenAI-compatible) -- if set, this is used
    # instead of talking to OpenAI directly for both chat and embeddings.
    litellm_endpoint: str | None = Field(default=None, validation_alias="AZURE_OPENAI_ENDPOINT_LITELLM")
    litellm_api_key_raw: str | None = Field(default=None, validation_alias="AZURE_OPENAI_API_KEY_LITELLM")

    embedding_backend: Literal["openai", "ollama"] = Field(
        default="openai", validation_alias="IC_AGENT_EMBEDDING_BACKEND"
    )
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_embedding_model: str = Field(
        default="nomic-embed-text", validation_alias="OLLAMA_EMBEDDING_MODEL"
    )

    log_level: str = Field(default="INFO", validation_alias="IC_AGENT_LOG_LEVEL")

    corpus_path: str = Field(
        default="corpus/similar_plans.yaml", validation_alias="IC_AGENT_CORPUS_PATH"
    )
    domain_config_dir: str = Field(
        default="config/domains", validation_alias="IC_AGENT_DOMAIN_DIR"
    )
    probe_budget_path: str = Field(
        default="config/probe_budget.yaml", validation_alias="IC_AGENT_PROBE_BUDGET_PATH"
    )
    usecase_docs_dir: str = Field(
        default="docs/metadata", validation_alias="IC_AGENT_USECASE_DOCS_DIR"
    )

    # Retrieval Layer (analysis_template_svc)
    retrieval_mode: Literal["mock", "http"] = Field(default="http", validation_alias="IC_AGENT_RETRIEVAL_MODE")
    retrieval_base_url: str = Field(
        default="http://localhost:7777", validation_alias="IC_AGENT_RETRIEVAL_BASE_URL"
    )
    retrieval_user_id: str = Field(
        default="agentic_experiment", validation_alias="IC_AGENT_RETRIEVAL_USER_ID"
    )
    retrieval_api_key: str | None = Field(default=None, validation_alias="INTERNAL_API_KEY")

    @property
    def litellm_base_url(self) -> str | None:
        """Base URL for the LiteLLM proxy's OpenAI-compatible API, or ``None``."""
        if not self.litellm_endpoint:
            return None
        return self.litellm_endpoint.rstrip("/") + "/v1"

    @property
    def litellm_api_key(self) -> str | None:
        """LiteLLM API key with any leading ``Bearer `` prefix stripped."""
        if not self.litellm_api_key_raw:
            return None
        return self.litellm_api_key_raw.removeprefix("Bearer ").strip()


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide ``Settings`` singleton."""
    return Settings()
