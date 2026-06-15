"""Models for the Decision Consultant (component 6).

Evaluates evidence quality. Cannot execute tools, cannot stop execution
-- it only evaluates the evidence ledger and reports gaps/confidence back
to the Decision Engine.
"""

from typing import Literal

from pydantic import BaseModel, Field

from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.planner_consultant import Hypothesis

GapCategory = Literal["closed", "partial", "open", "conflicting"]


class RemainingGap(BaseModel):
    description: str
    category: GapCategory


class DecisionConsultantInput(BaseModel):
    query: str
    ledger: list[EvidenceLedgerEntry] = Field(default_factory=list)


class DecisionConsultantOutput(BaseModel):
    relevant_probes: list[str] = Field(default_factory=list)
    irrelevant_probes: list[str] = Field(default_factory=list)
    remaining_gaps: list[RemainingGap] = Field(default_factory=list)
    new_hypotheses: list[Hypothesis] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
