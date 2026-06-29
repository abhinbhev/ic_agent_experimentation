import pytest

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_consultant import DecisionConsultantOutput, RemainingGap
from ic_agent.models.decision_engine import DecisionEngineInput, GapRecommendation
from ic_agent.models.planner_consultant import Hypothesis
from ic_agent.services.decision_engine_service import DecisionEngineService
from tests.conftest import FakeStructuredChatModel


def _service(sample_domain_config, sample_incremental_value_weights, recommendation=None):
    outputs = {
        GapRecommendation: [
            recommendation or GapRecommendation(recommended_next_gap=None, reason="r")
        ]
    }
    return DecisionEngineService(
        sample_domain_config,
        chat_model=FakeStructuredChatModel(outputs),
        weights=sample_incremental_value_weights,
    )


def test_weighted_score_and_continue(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],  # 2 relevant
        irrelevant_probes=[],
        remaining_gaps=[
            RemainingGap(description="pricing contribution", category="open"),
            RemainingGap(description="volume trend", category="closed"),
        ],
        new_hypotheses=[Hypothesis(id="H2", description="promo timing shift")],
        confidence=0.7,
    )
    service = _service(
        sample_domain_config,
        sample_incremental_value_weights,
        recommendation=GapRecommendation(
            recommended_next_gap="pricing contribution", reason="explains most of the gap"
        ),
    )

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=2,
            total_probes_completed=5,
            probe_budget=ProbeBudgetConfig(),
        )
    )

    b = output.value_breakdown
    # 2 relevant of 5 total -> 60% irrelevant
    assert b.irrelevance_score == pytest.approx(1 - 2 / 5)
    # confidence 0.7 -> low_confidence 0.3
    assert b.low_confidence_score == pytest.approx(0.3)
    assert b.unresolved_gaps_score == pytest.approx(0.5)  # 1 open out of 2
    assert b.new_hypotheses_score == pytest.approx(1 / 3)  # 1 new hypothesis / assumed max 3
    assert b.budget_headroom_score == pytest.approx(1 - 5 / 20)

    expected_total = (
        0.40 * b.unresolved_gaps_score
        + 0.30 * b.low_confidence_score
        + 0.20 * b.new_hypotheses_score
        + 0.05 * b.irrelevance_score
        + 0.05 * b.budget_headroom_score
    )
    assert output.expected_incremental_value == pytest.approx(expected_total)
    assert output.expected_incremental_value >= sample_incremental_value_weights.stop_threshold

    assert output.continue_ is True
    assert output.stop_reason == "continue"
    assert output.recommended_next_gap == "pricing contribution"


def test_stop_max_rounds_reached(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="open")],
        new_hypotheses=[],
        confidence=0.8,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=5,
            probes_completed_this_round=2,
            total_probes_completed=10,
            probe_budget=ProbeBudgetConfig(max_rounds=5),
        )
    )

    assert output.continue_ is False
    assert output.stop_reason == "max_rounds_reached"
    assert output.recommended_next_gap is None


def test_stop_max_total_probes_reached(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="open")],
        new_hypotheses=[],
        confidence=0.8,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=2,
            total_probes_completed=20,
            probe_budget=ProbeBudgetConfig(max_total_probes=20),
        )
    )

    assert output.continue_ is False
    assert output.stop_reason == "max_total_probes_reached"


def test_stop_all_major_gaps_closed(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="closed")],
        new_hypotheses=[],
        confidence=0.9,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=2,
            total_probes_completed=5,
            probe_budget=ProbeBudgetConfig(),
        )
    )

    assert output.continue_ is False
    assert output.stop_reason == "all_major_gaps_closed"


def test_stop_incremental_value_below_threshold(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    """A near-done state — most gaps closed, high confidence, fully relevant probes,
    no new hypotheses — should fall below the stop threshold and stop early."""
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[
            RemainingGap(description="closed-1", category="closed"),
            RemainingGap(description="closed-2", category="closed"),
            RemainingGap(description="closed-3", category="closed"),
            RemainingGap(description="closed-4", category="closed"),
            RemainingGap(description="minor partial", category="partial"),
        ],
        new_hypotheses=[],
        confidence=0.9,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=2,
            total_probes_completed=5,
            probe_budget=ProbeBudgetConfig(max_total_probes=20),
        )
    )

    assert output.expected_incremental_value < sample_incremental_value_weights.stop_threshold
    assert output.continue_ is False
    assert output.stop_reason == "incremental_value_below_threshold"


def test_stop_no_progress_this_round(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    """All probes in the current round are irrelevant — stall detected, stop early."""
    # Both fixture ledger entries are round_index=0; rounds_completed=0 → current round
    all_ids = [e.probe_id for e in sample_evidence_ledger]
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[],
        irrelevant_probes=all_ids,
        remaining_gaps=[RemainingGap(description="unknown term mapping", category="open")],
        new_hypotheses=[],
        confidence=0.3,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=0,
            probes_completed_this_round=2,
            total_probes_completed=2,
            probe_budget=ProbeBudgetConfig(),
        )
    )

    assert output.continue_ is False
    assert output.stop_reason == "no_progress_this_round"
    assert output.recommended_next_gap is None
    assert "progress" in output.reason.lower()


def test_stop_no_progress_zero_probes(
    sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights
):
    """Planner produced zero probes this round — stall detected even without irrelevant probe check."""
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="still open gap", category="open")],
        new_hypotheses=[],
        confidence=0.5,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=0,
            total_probes_completed=2,
            probe_budget=ProbeBudgetConfig(),
        )
    )

    assert output.continue_ is False
    assert output.stop_reason == "no_progress_this_round"
    assert output.recommended_next_gap is None
