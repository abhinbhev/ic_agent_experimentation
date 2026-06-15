from ic_agent.models.decision_consultant import DecisionConsultantInput, DecisionConsultantOutput, RemainingGap
from ic_agent.services.decision_consultant_service import DecisionConsultantService
from tests.conftest import FakeStructuredChatModel


def test_run_returns_fake_output(sample_domain_config, sample_evidence_ledger):
    fixed_output = DecisionConsultantOutput(
        relevant_probes=[e.probe_id for e in sample_evidence_ledger],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="open")],
        new_hypotheses=[],
        confidence=0.6,
    )
    chat_model = FakeStructuredChatModel({DecisionConsultantOutput: [fixed_output]})
    service = DecisionConsultantService(sample_domain_config, chat_model=chat_model)

    result = service.run(
        DecisionConsultantInput(
            query="Why did revenue decline in East China during Q1?",
            ledger=sample_evidence_ledger,
        )
    )

    assert result == fixed_output
    assert 0.0 <= result.confidence <= 1.0
