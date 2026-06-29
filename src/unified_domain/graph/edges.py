"""Conditional edge routing for the unified agent loop."""

from unified_domain.models.state import UnifiedAgentState


def route_after_decision_engine(state: UnifiedAgentState) -> str:
    """Route to "continue" (loop back to Planner Consultant) or "stop"
    (proceed to synthesis), based on the Decision Engine's output.
    """
    output = state["decision_engine_output"]
    return "continue" if output.continue_ else "stop"
