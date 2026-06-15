"""LangGraph state model.

``AgentState`` is a ``TypedDict`` (the form LangGraph's ``StateGraph``
expects) whose values are the pydantic models defined elsewhere in this
package. Each node converts the relevant slice of state into a pydantic
``*Input`` model, calls its service, and returns a partial-state update
dict built from the validated ``*Output`` model.
"""

from typing import TypedDict

from ic_agent.models.decision_consultant import DecisionConsultantOutput
from ic_agent.models.decision_engine import DecisionEngineOutput
from ic_agent.models.domain import DomainConfig
from ic_agent.models.evidence import EvidenceLedgerEntry
from ic_agent.models.planner import ToolCall
from ic_agent.models.planner_consultant import PlannerConsultantOutput
from ic_agent.models.similar_plan import MatchedPattern
from ic_agent.models.synthesizer import SynthesizerOutput


class AgentState(TypedDict, total=False):
    query: str
    domain_config: DomainConfig

    similar_patterns: list[MatchedPattern]
    consultant_plan: PlannerConsultantOutput | None
    tool_calls: list[ToolCall]

    evidence_ledger: list[EvidenceLedgerEntry]
    decision_consultant_output: DecisionConsultantOutput | None
    decision_engine_output: DecisionEngineOutput | None

    remaining_gaps: list[str]
    recommended_next_gap: str | None
    confidence: float

    rounds_completed: int
    probes_completed_this_round: int
    total_probes_completed: int

    final_answer: SynthesizerOutput | None
    stop_reason: str | None
