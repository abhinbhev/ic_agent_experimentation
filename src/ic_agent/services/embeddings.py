"""Embedding backends for the Similar Plan Service's Stage 2 hybrid search.

Default backend is OpenAI embeddings. An Ollama-based local backend is
wired in as an optional/swappable alternative -- if it isn't reachable,
``get_embedding_backend`` logs a warning and falls back to OpenAI.
"""

import logging
from abc import ABC, abstractmethod

import requests
from langchain_openai import OpenAIEmbeddings

from ic_agent.config.settings import Settings
from ic_agent.utils.ssl_setup import ensure_system_truststore

logger = logging.getLogger(__name__)


class EmbeddingBackendUnavailable(Exception):
    """Raised when a configured embedding backend cannot be reached."""


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...


class OpenAIEmbeddingBackend(EmbeddingBackend):
    def __init__(self, settings: Settings):
        if settings.litellm_base_url and settings.litellm_api_key:
            ensure_system_truststore()
            self._client = OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.litellm_api_key,
                base_url=settings.litellm_base_url,
            )
        else:
            self._client = OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
            )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed_query(text)


class OllamaEmbeddingBackend(EmbeddingBackend):
    def __init__(self, settings: Settings):
        try:
            requests.get(f"{settings.ollama_base_url}/api/tags", timeout=1)
        except requests.RequestException as exc:
            raise EmbeddingBackendUnavailable(
                f"Ollama not reachable at {settings.ollama_base_url}"
            ) from exc

        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:
            raise EmbeddingBackendUnavailable(
                "langchain-ollama is not installed (install the 'ollama' extra)"
            ) from exc

        self._client = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed_query(text)


def get_embedding_backend(settings: Settings) -> EmbeddingBackend:
    """Return the configured embedding backend, with graceful Ollama fallback."""
    if settings.embedding_backend == "ollama":
        try:
            return OllamaEmbeddingBackend(settings)
        except EmbeddingBackendUnavailable as exc:
            logger.warning("Ollama embedding backend unavailable (%s); falling back to OpenAI", exc)

    return OpenAIEmbeddingBackend(settings)
