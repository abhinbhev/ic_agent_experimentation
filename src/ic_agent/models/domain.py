"""Domain configuration models.

A ``DomainConfig`` describes the business context (datasets, metrics,
dimensions, business rules, terminology) that gets injected into the
``domain_prompt`` half of every service's prompt bundle. Loaded from
``config/domains/<domain_id>.yaml`` by ``config.domain_loader``.
"""

from pydantic import BaseModel, Field


class DatasetSpec(BaseModel):
    name: str
    description: str


class MetricSpec(BaseModel):
    name: str
    description: str
    unit: str | None = None


class DimensionSpec(BaseModel):
    name: str
    description: str
    example_values: list[str] = Field(default_factory=list)


class DomainConfig(BaseModel):
    domain_id: str
    display_name: str
    datasets: list[DatasetSpec] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    dimensions: list[DimensionSpec] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    terminology: dict[str, str] = Field(default_factory=dict)

    # Optional per-service overrides for the domain_prompt half of a
    # service's prompt bundle, keyed by service name (e.g.
    # "planner_consultant"). If absent, a template is rendered from the
    # fields above instead (see prompts.base.render_domain_prompt).
    domain_prompt_overrides: dict[str, str] = Field(default_factory=dict)
