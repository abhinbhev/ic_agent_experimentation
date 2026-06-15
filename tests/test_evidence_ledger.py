import pytest
from pydantic import ValidationError

from ic_agent.models.evidence import EvidenceLedgerEntry


def _entry(**overrides):
    defaults = dict(
        probe_id="P-aaaaaaaa",
        question="q",
        result="r",
        relevance_score=0.5,
        gap_closed="",
        created_at="2026-01-01T00:00:00+00:00",
        round_index=0,
    )
    defaults.update(overrides)
    return EvidenceLedgerEntry(**defaults)


def test_relevance_score_bounds():
    _entry(relevance_score=0.0)
    _entry(relevance_score=1.0)

    with pytest.raises(ValidationError):
        _entry(relevance_score=1.5)

    with pytest.raises(ValidationError):
        _entry(relevance_score=-0.1)


def test_ledger_accumulates_across_rounds(sample_evidence_ledger):
    ledger = list(sample_evidence_ledger)
    ledger.append(_entry(probe_id="P-cccccccc", round_index=1))

    assert len(ledger) == 3
    assert [e.round_index for e in ledger] == [0, 0, 1]
