"""Unified evidence models.

Extends the single-domain ``EvidenceLedgerEntry`` with cross-domain
provenance (``source_domain_id``) and the sub-agent's internal evidence
(``sub_evidence``), so the Unified Decision Consultant can evaluate both
high-level domain reports and granular sub-evidence quality.
"""

from pydantic import BaseModel, Field

from ic_agent.models.evidence import EvidenceLedgerEntry


class UnifiedEvidenceLedgerEntry(BaseModel):
    probe_id: str
    question: str
    source_domain_id: str
    result: str
    sub_evidence: list[EvidenceLedgerEntry] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    gap_closed: str = ""
    created_at: str = ""
    round_index: int = Field(ge=0, default=0)
