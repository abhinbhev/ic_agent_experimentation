"""Models for the Domain Router — the super-agent's equivalent of the
single-agent Planner.

Instead of selecting KPIs, the Domain Router assigns each probe candidate
to one or more sub-domains and formulates a domain-scoped business
question for each assignment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from ic_agent.models.domain import DomainConfig

if TYPE_CHECKING:
    from unified_domain.models.planner_consultant import UnifiedPlannerConsultantOutput


class DomainProbe(BaseModel):
    """A probe scoped to a single domain."""

    probe_candidate_id: str
    domain_id: str
    scoped_question: str
    expected_value: Literal["high", "medium", "low"]
    reason: str


class DomainAssignment(BaseModel):
    """Groups probes by domain for parallel execution."""

    domain_id: str
    domain_display_name: str
    probes: list[DomainProbe] = Field(default_factory=list)


class DomainRouterInput(BaseModel):
    consultant_plan: UnifiedPlannerConsultantOutput
    available_domains: list[DomainConfig]
    asked_questions: list[str] = Field(default_factory=list)


class DomainRouterOutput(BaseModel):
    assignments: list[DomainAssignment] = Field(default_factory=list)
