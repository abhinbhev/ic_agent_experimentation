"""Models for the Planner Consultant (component 2).

Converts a business question into an investigation plan. Cannot see
tools, cannot see APIs, cannot execute anything -- it reasons only in
terms of objectives, hypotheses, information gaps and evidence
requirements (Principle 1: planning is tool-agnostic).
"""

from typing import Literal

from pydantic import BaseModel, Field

from ic_agent.models.domain import DomainConfig
from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.similar_plan import MatchedPattern


class Hypothesis(BaseModel):
    id: str
    description: str
    status: Literal["open", "supported", "refuted"] = "open"


class ProbeCandidate(BaseModel):
    id: str
    goal: str
    expected_value: Literal["high", "medium", "low"]
    reason: str


class PlannerConsultantInput(BaseModel):
    query: str
    domain_context: DomainConfig
    similar_patterns: list[MatchedPattern] = Field(default_factory=list)

    # Accumulated context from prior loop iterations (empty on round 1).
    evidence_ledger: list[EvidenceLedgerEntry] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    recommended_next_gap: str | None = None


class PlannerConsultantOutput(BaseModel):
    objective: str
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    probe_candidates: list[ProbeCandidate] = Field(default_factory=list)
    success_criteria: str
    open_questions: list[str] = Field(default_factory=list)
