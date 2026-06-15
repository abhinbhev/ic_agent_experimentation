"""Retrieval Layer (component 4).

``RetrievalClient`` is the swappable transport: ``MockRetrievalClient``
returns a canned string (used in tests and as a network-free fallback),
``HttpRetrievalClient`` calls the real analysis_template_svc
(`/api/v1/analysis-template-executor/execute`). ``RetrievalService`` wraps
whichever client is configured; the input/output shapes
(``RetrievalQuery``/``RetrievalResult``) stay stable either way.
"""

import json
import logging
from abc import ABC, abstractmethod

import requests

from ic_agent.config.settings import Settings, get_settings
from ic_agent.models.retrieval import RetrievalQuery, RetrievalResult, Usecase
from ic_agent.utils.ids import new_probe_id

logger = logging.getLogger(__name__)

# Maps our internal usecase ids to analysis_template_svc usecase names.
_USECASE_TEMPLATE_MAP: dict[str, str] = {
    "brand_guidance": "gai_copilot_marketing_brand_guidance_ghq",
    "category": "gai_copilot_marketing_category_ghq",
}


class RetrievalClient(ABC):
    @abstractmethod
    def query(self, question: str, usecase: Usecase) -> str:
        ...


class MockRetrievalClient(RetrievalClient):
    def query(self, question: str, usecase: Usecase) -> str:
        return "Mock answer to: " + question


class HttpRetrievalClient(RetrievalClient):
    def __init__(self, settings: Settings):
        self._base_url = settings.retrieval_base_url.rstrip("/")
        self._user_id = settings.retrieval_user_id
        self._api_key = settings.retrieval_api_key

    def query(self, question: str, usecase: Usecase) -> str:
        template_usecase = _USECASE_TEMPLATE_MAP[usecase]
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-Internal-API-Key"] = self._api_key

        response = requests.post(
            f"{self._base_url}/api/v1/analysis-template-executor/execute",
            params={"user_id": self._user_id},
            json={
                "usecase": template_usecase,
                "user_question": question,
                "ner_heads": [],
                "request_id": new_probe_id(),
            },
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
        return self._extract_answer(response.json())

    @staticmethod
    def _extract_answer(data: dict) -> str:
        if data.get("error"):
            return f"Retrieval error: {data['error']}"

        raw_response = data.get("response", "")
        try:
            parsed = json.loads(raw_response)
            summary = parsed.get("Summary")
            if summary:
                return summary
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        return raw_response


def get_retrieval_client(settings: Settings | None = None) -> RetrievalClient:
    settings = settings or get_settings()
    if settings.retrieval_mode == "http":
        return HttpRetrievalClient(settings)
    return MockRetrievalClient()


class RetrievalService:
    def __init__(self, client: RetrievalClient | None = None):
        self._client = client or get_retrieval_client()

    def query(self, question: str, usecase: Usecase = "brand_guidance") -> str:
        logger.debug("RetrievalService: querying %r (usecase=%s)", question, usecase)
        return self._client.query(question, usecase)

    def query_structured(self, retrieval_query: RetrievalQuery) -> RetrievalResult:
        answer = self.query(retrieval_query.question, retrieval_query.usecase)
        return RetrievalResult(question=retrieval_query.question, answer=answer)
