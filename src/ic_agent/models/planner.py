"""Models for the Planner (component 3).

Translates probe goals into executable tool actions. Unlike the Planner
Consultant, the Planner knows about tools, APIs, execution constraints,
and the domain (KPIs, datasets, dimensions, terminology). For this
scaffold there is exactly one tool (``retrieval_query``).

The Planner Consultant proposes probe candidates as domain-agnostic,
directional goals (it knows nothing about KPIs or datasets). For each
candidate, the Planner uses the domain context to (1) rewrite the goal
into one or more concrete, KPI/dimension-grounded ``questions`` that the
retrieval layer can act on -- splitting into multiple simple, single-KPI
questions where the goal would otherwise require a compound question --
and (2) assign it to a retrieval ``usecase`` (see
``ic_agent.models.retrieval.Usecase``) using its own usecase knowledge
docs and schema metadata.
"""

from pydantic import BaseModel, Field

from ic_agent.models.planner_consultant import PlannerConsultantOutput
from ic_agent.models.retrieval import Usecase


class ToolCall(BaseModel):
    tool_name: str = "retrieval_query"
    probe_id: str
    question: str
    related_hypothesis_ids: list[str] = Field(default_factory=list)
    related_probe_candidate_id: str
    usecase: Usecase = "brand_guidance"
    reason: str = ""


class PlannerInput(BaseModel):
    consultant_plan: PlannerConsultantOutput
    asked_questions: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    tool_calls: list[ToolCall] = Field(default_factory=list)


class QuestionItem(BaseModel):
    text: str
    keep: bool = True


class ProbeUsecaseAssignment(BaseModel):
    probe_candidate_id: str
    questions: list[QuestionItem] = Field(default_factory=list)
    usecase: Usecase
    reason: str


class PlannerUsecaseAssignments(BaseModel):
    assignments: list[ProbeUsecaseAssignment] = Field(default_factory=list)
