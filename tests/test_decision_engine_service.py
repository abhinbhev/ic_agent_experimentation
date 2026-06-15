import pytest

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_consultant import DecisionConsultantOutput, RemainingGap
from ic_agent.models.decision_engine import DecisionEngineInput, GapRecommendation
from ic_agent.models.planner_consultant import Hypothesis
from ic_agent.services.decision_engine_service import DecisionEngineService
from tests.conftest import FakeStructuredChatModel


def _service(sample_domain_config, sample_incremental_value_weights, recommendation=None):
    outputs = {GapRecommendation: [recommendation or GapRecommendation(recommended_next_gap=None, reason="r")]}
    return DecisionEngineService(
        sample_domain_config,
        chat_model=FakeStructuredChatModel(outputs),
        weights=sample_incremental_value_weights,
    )


def test_weighted_score_and_continue(sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights):
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
        recommendation=GapRecommendation(recommended_next_gap="pricing contribution", reason="explains most of the gap"),
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
    assert b.evidence_coverage == pytest.approx(2 / 5)
    assert b.confidence == pytest.approx(0.7)
    assert b.remaining_gaps_score == pytest.approx(0.5)  # 1 open out of 2
    assert b.alternative_hypotheses_score == pytest.approx(1 / 3)  # 1 new hypothesis / assumed max 3
    assert b.probe_cost_score == pytest.approx(1 - 5 / 20)

    expected_total = (
        0.30 * b.evidence_coverage
        + 0.25 * b.confidence
        + 0.20 * b.remaining_gaps_score
        + 0.15 * b.alternative_hypotheses_score
        + 0.10 * b.probe_cost_score
    )
    assert output.expected_incremental_value == pytest.approx(expected_total)
    assert output.expected_incremental_value >= sample_incremental_value_weights.stop_threshold

    assert output.continue_ is True
    assert output.stop_reason == "continue"
    assert output.recommended_next_gap == "pricing contribution"


def test_stop_max_rounds_reached(sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights):
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


def test_stop_max_total_probes_reached(sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights):
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


def test_stop_all_major_gaps_closed(sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights):
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


def test_stop_incremental_value_below_threshold(sample_domain_config, sample_evidence_ledger, sample_incremental_value_weights):
    consultant_output = DecisionConsultantOutput(
        relevant_probes=[],
        irrelevant_probes=[e.probe_id for e in sample_evidence_ledger],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="open")],
        new_hypotheses=[],
        confidence=0.1,
    )
    service = _service(sample_domain_config, sample_incremental_value_weights)

    output = service.run(
        DecisionEngineInput(
            ledger=sample_evidence_ledger,
            decision_consultant_output=consultant_output,
            rounds_completed=1,
            probes_completed_this_round=2,
            total_probes_completed=19,
            probe_budget=ProbeBudgetConfig(max_total_probes=20),
        )
    )

    assert output.expected_incremental_value < sample_incremental_value_weights.stop_threshold
    assert output.continue_ is False
    assert output.stop_reason == "incremental_value_below_threshold"
