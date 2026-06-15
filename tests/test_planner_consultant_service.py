from ic_agent.models.planner_consultant import (
    Hypothesis,
    PlannerConsultantInput,
    PlannerConsultantOutput,
    ProbeCandidate,
)
from ic_agent.services.planner_consultant_service import PlannerConsultantService
from tests.conftest import FakeStructuredChatModel


def test_run_returns_fake_output(sample_domain_config):
    fixed_output = PlannerConsultantOutput(
        objective="Explain the East China revenue decline.",
        hypotheses=[Hypothesis(id="H1", description="Volume dropped")],
        probe_candidates=[
            ProbeCandidate(id="P1", goal="Check volume trend", expected_value="high", reason="primary driver")
        ],
        success_criteria="Top drivers explain majority of change",
        open_questions=["Was there a promotion change?"],
    )
    chat_model = FakeStructuredChatModel({PlannerConsultantOutput: [fixed_output]})
    service = PlannerConsultantService(chat_model=chat_model)

    result = service.run(
        PlannerConsultantInput(
            query="Why did revenue decline in East China during Q1?",
            domain_context=sample_domain_config,
        )
    )

    assert result == fixed_output
