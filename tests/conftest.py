"""Shared pytest fixtures and test doubles.

None of these require network access or ``OPENAI_API_KEY``.
"""

import hashlib

import pytest

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.probe_budget import IncrementalValueWeights, ProbeBudgetConfig, ScoreFusionWeights
from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.services.embeddings import EmbeddingBackend


class _QueueRunnable:
    """Minimal Runnable-like object: ``invoke`` pops from a queue of
    pre-set outputs (repeating the last one once exhausted)."""

    def __init__(self, outputs: list):
        self._outputs = list(outputs)

    def invoke(self, *args, **kwargs):
        if len(self._outputs) > 1:
            return self._outputs.pop(0)
        return self._outputs[0]


class FakeStructuredChatModel:
    """Duck-typed stand-in for ``BaseChatModel``.

    Only implements ``with_structured_output``, which is all the
    LLM-backed services in this project call. ``outputs_by_schema`` maps
    a pydantic model class to a list of instances to return in order
    (the last is repeated once the list is exhausted).
    """

    def __init__(self, outputs_by_schema: dict[type, list] | None = None):
        self._outputs_by_schema = outputs_by_schema or {}

    def with_structured_output(self, schema: type):
        outputs = self._outputs_by_schema.get(schema)
        if not outputs:
            raise KeyError(f"FakeStructuredChatModel has no configured output for {schema}")
        return _QueueRunnable(outputs)


class StubEmbeddingBackend(EmbeddingBackend):
    """Deterministic, network-free embedding backend for tests."""

    def __init__(self, dim: int = 8):
        self._dim = dim

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: self._dim]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
def sample_domain_config():
    return load_domain_config("example")


@pytest.fixture
def sample_evidence_ledger():
    return [
        EvidenceLedgerEntry(
            probe_id="P-aaaaaaaa",
            question="What was the revenue trend in East China last quarter?",
            result="Mock answer to: What was the revenue trend in East China last quarter?",
            relevance_score=0.0,
            gap_closed="",
            created_at="2026-01-01T00:00:00+00:00",
            round_index=0,
        ),
        EvidenceLedgerEntry(
            probe_id="P-bbbbbbbb",
            question="How did volume change in East China last quarter?",
            result="Mock answer to: How did volume change in East China last quarter?",
            relevance_score=0.0,
            gap_closed="",
            created_at="2026-01-01T00:01:00+00:00",
            round_index=0,
        ),
    ]


@pytest.fixture
def sample_probe_budget():
    return ProbeBudgetConfig()


@pytest.fixture
def sample_score_fusion_weights():
    return ScoreFusionWeights()


@pytest.fixture
def sample_incremental_value_weights():
    return IncrementalValueWeights()


@pytest.fixture
def stub_embedding_backend():
    return StubEmbeddingBackend()
