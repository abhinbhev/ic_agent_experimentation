"""Models for the Unified Planner Consultant.

Mirrors the single-agent's ``PlannerConsultantOutput`` but adds
``available_domains`` and ``domain_knowledge_doc`` to the input so the
LLM understands the cross-domain landscape.
"""

from typing import Literal

from pydantic import BaseModel, Field

from ic_agent.models.domain import DomainConfig
from ic_agent.models.similar_plan import MatchedPattern
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry


class UnifiedHypothesis(BaseModel):
    id: str
    description: str
    status: Literal["open", "supported", "refuted"] = "open"


class UnifiedProbeCandidate(BaseModel):
    id: str
    goal: str
    expected_value: Literal["high", "medium", "low"]
    reason: str


class UnifiedPlannerConsultantInput(BaseModel):
    query: str
    available_domains: list[DomainConfig] = Field(default_factory=list)
    domain_knowledge_doc: str = ""
    similar_patterns: list[MatchedPattern] = Field(default_factory=list)
    evidence_ledger: list[UnifiedEvidenceLedgerEntry] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    recommended_next_gap: str | None = None


class UnifiedPlannerConsultantOutput(BaseModel):
    objective: str
    hypotheses: list[UnifiedHypothesis] = Field(default_factory=list)
    probe_candidates: list[UnifiedProbeCandidate] = Field(default_factory=list)
    success_criteria: str
    open_questions: list[str] = Field(default_factory=list)
