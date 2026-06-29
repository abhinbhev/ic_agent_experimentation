"""Models for the Unified Decision Consultant.

Same gap categorisation as the single-agent, but evidence entries carry
``source_domain_id`` so the consultant can evaluate cross-domain coverage.
"""

from typing import Literal

from pydantic import BaseModel, Field

from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.models.planner_consultant import UnifiedHypothesis

GapCategory = Literal["closed", "partial", "open", "conflicting"]


class UnifiedRemainingGap(BaseModel):
    description: str
    category: GapCategory


class UnifiedDecisionConsultantInput(BaseModel):
    query: str
    ledger: list[UnifiedEvidenceLedgerEntry] = Field(default_factory=list)


class UnifiedDecisionConsultantOutput(BaseModel):
    relevant_probes: list[str] = Field(default_factory=list)
    irrelevant_probes: list[str] = Field(default_factory=list)
    remaining_gaps: list[UnifiedRemainingGap] = Field(default_factory=list)
    new_hypotheses: list[UnifiedHypothesis] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
