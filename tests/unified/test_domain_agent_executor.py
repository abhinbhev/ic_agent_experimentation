"""Tests for DomainAgentExecutor.

All tests mock ``build_app`` and ``load_domain_config`` so no LLM calls
or real YAML files are needed.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch


from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.synthesizer import SynthesizerOutput
from unified_domain.models.domain_router import DomainAssignment, DomainProbe
from unified_domain.services.domain_agent_executor import DomainAgentExecutor


# ── helpers ──────────────────────────────────────────────────────────


def _make_fake_graph(final_state: dict):
    """Return an object whose ``ainvoke`` resolves to *final_state*."""
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value=final_state)
    return graph


def _make_probe(
    domain_id: str = "example",
    question: str = "What is X?",
    probe_id: str = "PC-1",
) -> DomainProbe:
    return DomainProbe(
        probe_candidate_id=probe_id,
        domain_id=domain_id,
        scoped_question=question,
        expected_value="high",
        reason="test",
    )


def _make_assignment(
    domain_id: str = "example",
    probes: list[DomainProbe] | None = None,
) -> DomainAssignment:
    return DomainAssignment(
        domain_id=domain_id,
        domain_display_name=domain_id.replace("_", " ").title(),
        probes=probes or [_make_probe(domain_id=domain_id)],
    )


_SUB_EVIDENCE = [
    EvidenceLedgerEntry(
        probe_id="P-sub1",
        question="sub question",
        result="sub result",
        relevance_score=0.8,
        created_at="2026-01-01T00:00:00+00:00",
        round_index=0,
    )
]

_FINAL_STATE = {
    "final_answer": SynthesizerOutput(markdown="## Summary\nAll good.", confidence=0.9),
    "evidence_ledger": _SUB_EVIDENCE,
}


# ── tests ────────────────────────────────────────────────────────────


@patch("unified_domain.services.domain_agent_executor.load_domain_config")
@patch("unified_domain.services.domain_agent_executor.build_app")
def test_executes_single_domain(mock_build_app, mock_load_cfg, sample_domain_config):
    """One assignment / one probe → one UnifiedEvidenceLedgerEntry."""
    mock_load_cfg.return_value = sample_domain_config
    mock_build_app.return_value = _make_fake_graph(_FINAL_STATE)

    executor = DomainAgentExecutor(settings=None)
    entries = executor.execute_sync([_make_assignment()], round_index=0)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.source_domain_id == "example"
    assert "All good" in entry.result
    assert len(entry.sub_evidence) == 1
    assert entry.sub_evidence[0].probe_id == "P-sub1"
    assert entry.round_index == 0
    assert entry.probe_id.startswith("P-")


@patch("unified_domain.services.domain_agent_executor.load_domain_config")
@patch("unified_domain.services.domain_agent_executor.build_app")
def test_parallel_execution(mock_build_app, mock_load_cfg, sample_domain_config):
    """Two domains with a simulated delay — should run concurrently."""
    mock_load_cfg.return_value = sample_domain_config

    async def _slow_invoke(*args, **kwargs):
        await asyncio.sleep(0.3)
        return _FINAL_STATE

    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(side_effect=_slow_invoke)
    mock_build_app.return_value = fake_graph

    assignments = [
        _make_assignment(domain_id="domain_a"),
        _make_assignment(domain_id="domain_b"),
    ]

    executor = DomainAgentExecutor(settings=None)
    t0 = time.perf_counter()
    entries = executor.execute_sync(assignments, round_index=1)
    elapsed = time.perf_counter() - t0

    assert len(entries) == 2
    domains = {e.source_domain_id for e in entries}
    assert domains == {"domain_a", "domain_b"}
    # Both sleep 0.3s; sequential would be ≥0.6s. Parallel should be <0.5s.
    assert elapsed < 0.55, f"Expected parallel execution but took {elapsed:.2f}s"


@patch("unified_domain.services.domain_agent_executor.load_domain_config")
@patch("unified_domain.services.domain_agent_executor.build_app")
def test_handles_domain_agent_error(mock_build_app, mock_load_cfg, sample_domain_config):
    """If the sub-agent raises, we get an error entry instead of a crash."""
    mock_load_cfg.return_value = sample_domain_config
    mock_build_app.side_effect = RuntimeError("kaboom")

    executor = DomainAgentExecutor(settings=None)
    entries = executor.execute_sync([_make_assignment()], round_index=0)

    assert len(entries) == 1
    entry = entries[0]
    assert "Domain agent error: kaboom" in entry.result
    assert entry.sub_evidence == []
    assert entry.source_domain_id == "example"


@patch("unified_domain.services.domain_agent_executor.load_domain_config")
@patch("unified_domain.services.domain_agent_executor.build_app")
def test_multiple_probes_in_single_domain(mock_build_app, mock_load_cfg, sample_domain_config):
    """Multiple probes within one assignment produce one entry each."""
    mock_load_cfg.return_value = sample_domain_config
    mock_build_app.return_value = _make_fake_graph(_FINAL_STATE)

    probes = [
        _make_probe(question="Q1?", probe_id="PC-1"),
        _make_probe(question="Q2?", probe_id="PC-2"),
    ]
    assignment = _make_assignment(probes=probes)

    executor = DomainAgentExecutor(settings=None)
    entries = executor.execute_sync([assignment], round_index=0)

    assert len(entries) == 2
    questions = {e.question for e in entries}
    assert questions == {"Q1?", "Q2?"}
