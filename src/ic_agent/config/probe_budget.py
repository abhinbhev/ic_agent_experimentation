"""Probe budget controls and Incremental Value Framework weights.

These tunables live in ``config/probe_budget.yaml`` so they can be
adjusted without touching code (Additional Instructions: "Separate
configs and env variables cleanly").
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class ProbeBudgetConfig(BaseModel):
    max_rounds: int = Field(default=5, gt=0)
    max_probes_per_round: int = Field(default=6, gt=0)
    max_total_probes: int = Field(default=20, gt=0)


class ScoreFusionWeights(BaseModel):
    """Stage 3 score-fusion configuration for the Similar Plan Service."""

    bm25_weight: float = 0.5
    embedding_weight: float = 0.5
    fusion_method: Literal["weighted_sum", "rrf"] = "weighted_sum"
    rrf_k: int = 60


class IncrementalValueWeights(BaseModel):
    """Weights for the Decision Engine's Incremental Value Framework."""

    evidence_coverage: float = 0.30
    confidence: float = 0.25
    remaining_gaps: float = 0.20
    alternative_hypotheses: float = 0.15
    probe_cost: float = 0.10
    stop_threshold: float = 0.35

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "IncrementalValueWeights":
        total = (
            self.evidence_coverage
            + self.confidence
            + self.remaining_gaps
            + self.alternative_hypotheses
            + self.probe_cost
        )
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Incremental value weights must sum to ~1.0, got {total}")
        return self


class ProbeBudgetSettings(BaseModel):
    """Container for everything loaded from ``probe_budget.yaml``."""

    probe_budget: ProbeBudgetConfig = Field(default_factory=ProbeBudgetConfig)
    score_fusion: ScoreFusionWeights = Field(default_factory=ScoreFusionWeights)
    incremental_value_weights: IncrementalValueWeights = Field(
        default_factory=IncrementalValueWeights
    )


def load_probe_budget_settings(path: str | Path | None = None) -> ProbeBudgetSettings:
    """Load probe budget / score-fusion / incremental-value config from YAML.

    Falls back to defaults for any section (or the whole file) that is
    missing.
    """
    if path is None:
        return ProbeBudgetSettings()

    file_path = Path(path)
    if not file_path.exists():
        return ProbeBudgetSettings()

    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return ProbeBudgetSettings.model_validate(data)
