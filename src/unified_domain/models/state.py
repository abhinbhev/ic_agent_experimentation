"""LangGraph state model for the unified (super-agent) pipeline.

Mirrors ``ic_agent.models.state.AgentState`` but operates at the
cross-domain level: evidence is tagged with ``source_domain_id``,
the router replaces the planner, and domain-agent reports are stored
alongside the granular sub-evidence.
"""

from typing import TYPE_CHECKING, Any, TypedDict

from ic_agent.models.decision_engine import DecisionEngineOutput
from ic_agent.models.domain import DomainConfig
from ic_agent.models.similar_plan import MatchedPattern
from ic_agent.models.synthesizer import SynthesizerOutput
from unified_domain.models.decision_consultant import UnifiedDecisionConsultantOutput
from unified_domain.models.domain_router import DomainAssignment
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.models.planner_consultant import UnifiedPlannerConsultantOutput

if TYPE_CHECKING:  # avoid runtime import cycle
    pass


class UnifiedAgentState(TypedDict, total=False):
    query: str
    available_domains: list[DomainConfig]
    domain_knowledge_doc: str

    # Similar plan (cross-domain)
    similar_patterns: list[MatchedPattern]

    # Planning
    consultant_plan: UnifiedPlannerConsultantOutput | None
    domain_assignments: list[DomainAssignment]

    # Evidence (cross-domain)
    evidence_ledger: list[UnifiedEvidenceLedgerEntry]

    # Decision
    decision_consultant_output: UnifiedDecisionConsultantOutput | None
    decision_engine_output: DecisionEngineOutput | None

    # Loop control
    remaining_gaps: list[str]
    recommended_next_gap: str | None
    confidence: float
    rounds_completed: int
    probes_completed_this_round: int
    total_probes_completed: int

    # Final
    final_answer: SynthesizerOutput | None
    stop_reason: str | None

    # Observability — optional EventBus for the live question-graph UI.
    # Typed as Any to avoid a circular import at module load.
    event_bus: Any
