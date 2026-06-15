from ic_agent.graph.edges import route_after_decision_engine
from ic_agent.models.decision_engine import DecisionEngineOutput, IncrementalValueBreakdown


def _decision_engine_output(continue_: bool, stop_reason: str) -> DecisionEngineOutput:
    breakdown = IncrementalValueBreakdown(
        evidence_coverage=0.5,
        confidence=0.5,
        remaining_gaps_score=0.5,
        alternative_hypotheses_score=0.5,
        probe_cost_score=0.5,
        weighted_total=0.5,
    )
    return DecisionEngineOutput(
        **{"continue": continue_},
        expected_incremental_value=breakdown.weighted_total,
        recommended_next_gap=None,
        reason="r",
        stop_reason=stop_reason,
        value_breakdown=breakdown,
    )


def test_route_continue():
    state = {"decision_engine_output": _decision_engine_output(True, "continue")}
    assert route_after_decision_engine(state) == "continue"


def test_route_stop():
    state = {"decision_engine_output": _decision_engine_output(False, "all_major_gaps_closed")}
    assert route_after_decision_engine(state) == "stop"
