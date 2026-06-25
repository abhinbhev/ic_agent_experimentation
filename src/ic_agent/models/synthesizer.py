"""Models for the Final Answer Synthesizer (component 8).

Converts accumulated evidence into a user-facing markdown answer with
Summary, Key Findings, Evidence, Recommendations, Confidence and
Remaining Unknowns sections.
"""

from pydantic import BaseModel, Field

from ic_agent.models.decision_consultant import DecisionConsultantOutput
from ic_agent.models.evidence import EvidenceLedgerEntry


class SynthesizerInput(BaseModel):
    query: str
    ledger: list[EvidenceLedgerEntry] = Field(default_factory=list)
    decision_consultant_output: DecisionConsultantOutput | None = None
    stop_reason: str
    usecase_docs: dict[str, str] = Field(default_factory=dict)
    schema_doc: str | None = None


class SynthesizerOutput(BaseModel):
    markdown: str
    confidence: float = Field(ge=0.0, le=1.0)
