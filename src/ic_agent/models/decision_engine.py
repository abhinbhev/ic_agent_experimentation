"""Models for the Decision Engine (component 7).

Determines whether another probe cycle is worthwhile. The core question
is not "can I answer?" but "is another probe likely to improve answer
quality enough to justify cost?" (Principle 3).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_consultant import DecisionConsultantOutput
from ic_agent.models.evidence import EvidenceLedgerEntry

StopReason = Literal[
    "incremental_value_below_threshold",
    "max_rounds_reached",
    "max_total_probes_reached",
    "all_major_gaps_closed",
    "no_progress_this_round",
    "continue",
]


class DecisionEngineInput(BaseModel):
    ledger: list[EvidenceLedgerEntry] = Field(default_factory=list)
    decision_consultant_output: DecisionConsultantOutput
    rounds_completed: int = Field(ge=0)
    probes_completed_this_round: int = Field(ge=0)
    total_probes_completed: int = Field(ge=0)
    probe_budget: ProbeBudgetConfig


class IncrementalValueBreakdown(BaseModel):
    """Transparency record of the weighted Incremental Value Framework score."""

    evidence_coverage: float
    confidence: float
    remaining_gaps_score: float
    alternative_hypotheses_score: float
    probe_cost_score: float
    weighted_total: float


class DecisionEngineOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    continue_: bool = Field(alias="continue")
    expected_incremental_value: float
    recommended_next_gap: str | None = None
    reason: str
    stop_reason: StopReason = "continue"
    value_breakdown: IncrementalValueBreakdown


class GapRecommendation(BaseModel):
    """Structured output of the Decision Engine's small LLM call.

    Only used when there is genuine qualitative reasoning to do (i.e. not
    for budget-exhaustion stop conditions, which are deterministic).
    """

    recommended_next_gap: str | None = None
    reason: str
