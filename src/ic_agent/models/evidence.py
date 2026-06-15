"""Evidence Ledger models (component 5).

The ledger is persistent memory across loop iterations. Decision services
must always read the full ledger, never only the latest probe.
"""

from pydantic import BaseModel, Field


class EvidenceLedgerEntry(BaseModel):
    probe_id: str
    question: str
    result: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    gap_closed: str = ""
    created_at: str
    round_index: int = Field(ge=0)
