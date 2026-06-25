from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.planner import (
    PlannerInput,
    PlannerUsecaseAssignments,
    ProbeUsecaseAssignment,
    QuestionItem,
)
from ic_agent.models.planner_consultant import Hypothesis, PlannerConsultantOutput, ProbeCandidate
from ic_agent.services.planner_service import PlannerService
from tests.conftest import FakeStructuredChatModel

_USECASE_DOCS = {"brand_guidance": "brand guidance doc", "category": "category doc"}


def _consultant_plan(*candidates: ProbeCandidate) -> PlannerConsultantOutput:
    return PlannerConsultantOutput(
        objective="obj",
        hypotheses=[Hypothesis(id="H1", description="h1")],
        probe_candidates=list(candidates),
        success_criteria="criteria",
        open_questions=[],
    )


def _planner_service(sample_domain_config, probe_budget, assignments):
    chat_model = FakeStructuredChatModel(
        {PlannerUsecaseAssignments: [PlannerUsecaseAssignments(assignments=assignments)]}
    )
    return PlannerService(
        sample_domain_config, _USECASE_DOCS, chat_model=chat_model, probe_budget=probe_budget
    )


def test_tool_calls_capped_and_ordered_by_expected_value(sample_domain_config):
    plan = _consultant_plan(
        ProbeCandidate(id="P1", goal="low value", expected_value="low", reason="r"),
        ProbeCandidate(id="P2", goal="high value", expected_value="high", reason="r"),
        ProbeCandidate(id="P3", goal="medium value", expected_value="medium", reason="r"),
    )
    service = _planner_service(
        sample_domain_config,
        ProbeBudgetConfig(max_probes_per_round=2),
        assignments=[
            ProbeUsecaseAssignment(
                probe_candidate_id="P2",
                questions=[QuestionItem(text="rewritten high value")],
                usecase="brand_guidance",
                reason="r",
            ),
            ProbeUsecaseAssignment(
                probe_candidate_id="P3",
                questions=[QuestionItem(text="rewritten medium value")],
                usecase="category",
                reason="r",
            ),
        ],
    )

    output = service.run(PlannerInput(consultant_plan=plan))

    assert len(output.tool_calls) == 2
    assert output.tool_calls[0].related_probe_candidate_id == "P2"  # high
    assert output.tool_calls[1].related_probe_candidate_id == "P3"  # medium
    assert output.tool_calls[0].question == "rewritten high value"
    assert output.tool_calls[0].usecase == "brand_guidance"
    assert output.tool_calls[1].usecase == "category"


def test_tool_call_ids_are_unique(sample_domain_config):
    plan = _consultant_plan(
        ProbeCandidate(id="P1", goal="a", expected_value="high", reason="r"),
        ProbeCandidate(id="P2", goal="b", expected_value="high", reason="r"),
    )
    service = _planner_service(
        sample_domain_config,
        ProbeBudgetConfig(max_probes_per_round=6),
        assignments=[
            ProbeUsecaseAssignment(
                probe_candidate_id="P1",
                questions=[QuestionItem(text="q1")],
                usecase="brand_guidance",
                reason="r",
            ),
            ProbeUsecaseAssignment(
                probe_candidate_id="P2",
                questions=[QuestionItem(text="q2")],
                usecase="brand_guidance",
                reason="r",
            ),
        ],
    )

    output = service.run(PlannerInput(consultant_plan=plan))

    probe_ids = {tc.probe_id for tc in output.tool_calls}
    assert len(probe_ids) == 2


def test_missing_assignment_falls_back_to_default_usecase(sample_domain_config):
    plan = _consultant_plan(
        ProbeCandidate(id="P1", goal="a", expected_value="high", reason="r"),
    )
    service = _planner_service(
        sample_domain_config,
        ProbeBudgetConfig(max_probes_per_round=6),
        assignments=[],  # LLM returned no assignments
    )

    output = service.run(PlannerInput(consultant_plan=plan))

    assert output.tool_calls[0].usecase == "brand_guidance"


def test_one_assignment_can_expand_to_multiple_tool_calls(sample_domain_config):
    plan = _consultant_plan(
        ProbeCandidate(id="P1", goal="overall brand health", expected_value="high", reason="r"),
    )
    service = _planner_service(
        sample_domain_config,
        ProbeBudgetConfig(max_probes_per_round=6),
        assignments=[
            ProbeUsecaseAssignment(
                probe_candidate_id="P1",
                questions=[
                    QuestionItem(text="What is the Power of Brand X in Country Y?"),
                    QuestionItem(text="What is the Salience of Brand X in Country Y?"),
                ],
                usecase="brand_guidance",
                reason="split by KPI",
            ),
        ],
    )

    output = service.run(PlannerInput(consultant_plan=plan))

    assert len(output.tool_calls) == 2
    assert {tc.related_probe_candidate_id for tc in output.tool_calls} == {"P1"}
    assert len({tc.probe_id for tc in output.tool_calls}) == 2
    questions = {tc.question for tc in output.tool_calls}
    assert questions == {
        "What is the Power of Brand X in Country Y?",
        "What is the Salience of Brand X in Country Y?",
    }


def test_expanded_tool_calls_are_capped_at_max_probes_per_round(sample_domain_config):
    plan = _consultant_plan(
        ProbeCandidate(id="P1", goal="overall brand health", expected_value="high", reason="r"),
    )
    service = _planner_service(
        sample_domain_config,
        ProbeBudgetConfig(max_probes_per_round=1),
        assignments=[
            ProbeUsecaseAssignment(
                probe_candidate_id="P1",
                questions=[
                    QuestionItem(text="question 1"),
                    QuestionItem(text="question 2"),
                    QuestionItem(text="question 3"),
                ],
                usecase="brand_guidance",
                reason="split by KPI",
            ),
        ],
    )

    output = service.run(PlannerInput(consultant_plan=plan))

    assert len(output.tool_calls) == 1
