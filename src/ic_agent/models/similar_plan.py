"""Models for the Similar Plan Service (component 1).

The Similar Plan Service provides planning precedents only -- it never
returns answers or data, only reasoning/probe patterns matched from a
corpus of archetypes (see corpus/similar_plans.yaml).
"""

from pydantic import BaseModel, Field

from ic_agent.models.domain import DomainConfig


class SimilarPlanEntry(BaseModel):
    """A single archetype record in the similar-plan corpus."""

    id: str
    intent: str
    dataset_family: list[str] = Field(default_factory=list)
    analysis_type: str
    probe_sequence: list[str]
    failure_modes: list[str] = Field(default_factory=list)
    stop_condition: str
    description: str = ""


class SimilarPlanQuery(BaseModel):
    """Input to ``SimilarPlanService.search``."""

    user_query: str
    domain_context: DomainConfig


class MatchedPattern(BaseModel):
    """A single matched archetype returned to the Planner Consultant."""

    pattern_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    probe_strategy: list[str]


class SimilarPlanResult(BaseModel):
    """Output of ``SimilarPlanService.search``."""

    matched_patterns: list[MatchedPattern] = Field(default_factory=list)
