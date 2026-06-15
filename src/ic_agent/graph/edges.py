"""Conditional edge routing for the agent loop."""

from ic_agent.models.state import AgentState


def route_after_decision_engine(state: AgentState) -> str:
    """Route to "continue" (loop back to Planner Consultant) or "stop"
    (proceed to synthesis), based on the Decision Engine's output.

    All budget/threshold logic is resolved inside
    ``DecisionEngineService.run`` -- this is a thin dispatcher.
    """
    output = state["decision_engine_output"]
    return "continue" if output.continue_ else "stop"
