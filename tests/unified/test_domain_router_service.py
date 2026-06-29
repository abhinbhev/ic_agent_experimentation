"""Tests for the Domain Router service."""

from ic_agent.config.probe_budget import ProbeBudgetConfig
from tests.conftest import FakeStructuredChatModel
from unified_domain.models.planner_consultant import (
    UnifiedPlannerConsultantOutput,
    UnifiedProbeCandidate,
)
from unified_domain.models.domain_router import (
    DomainAssignment,
    DomainProbe,
    DomainRouterInput,
    DomainRouterOutput,
)
from unified_domain.services.domain_router_service import DomainRouterService

# Resolve the forward reference so pydantic can validate DomainRouterInput
DomainRouterInput.model_rebuild()


def _make_consultant_output(*probes: UnifiedProbeCandidate) -> UnifiedPlannerConsultantOutput:
    return UnifiedPlannerConsultantOutput(
        objective="test objective",
        hypotheses=[],
        probe_candidates=list(probes),
        success_criteria="test",
        open_questions=[],
    )


class TestDomainRouterService:
    def test_routes_probes_to_domains(self, sample_domain_config):
        """Two probes assigned to two different domains."""
        probe_a = UnifiedProbeCandidate(
            id="P1",
            goal="How is brand health trending in Brazil?",
            expected_value="high",
            reason="core question",
        )
        probe_b = UnifiedProbeCandidate(
            id="P2",
            goal="What is the consumption pattern in Brazil?",
            expected_value="medium",
            reason="secondary question",
        )

        fake_output = DomainRouterOutput(
            assignments=[
                DomainAssignment(
                    domain_id="example",
                    domain_display_name="Example Domain",
                    probes=[
                        DomainProbe(
                            probe_candidate_id="P1",
                            domain_id="example",
                            scoped_question="What is the brand health of Budweiser in Brazil in Q1 2026?",
                            expected_value="high",
                            reason="Sales dataset covers brand health",
                        ),
                    ],
                ),
                DomainAssignment(
                    domain_id="category",
                    domain_display_name="Category Domain",
                    probes=[
                        DomainProbe(
                            probe_candidate_id="P2",
                            domain_id="category",
                            scoped_question="What is the consumption of beer in Brazil in Q1 2026?",
                            expected_value="medium",
                            reason="Category dataset covers consumption",
                        ),
                    ],
                ),
            ]
        )

        chat_model = FakeStructuredChatModel({DomainRouterOutput: [fake_output]})
        service = DomainRouterService(chat_model=chat_model)

        result = service.run(
            DomainRouterInput(
                consultant_plan=_make_consultant_output(probe_a, probe_b),
                available_domains=[sample_domain_config],
                asked_questions=[],
            )
        )

        assert len(result.assignments) == 2
        assert result.assignments[0].domain_id == "example"
        assert result.assignments[1].domain_id == "category"
        assert result.assignments[0].probes[0].probe_candidate_id == "P1"
        assert result.assignments[1].probes[0].probe_candidate_id == "P2"

    def test_caps_at_max_probes_per_round(self, sample_domain_config):
        """Five probes with max_probes_per_round=2 — only 2 survive."""
        probes = [
            UnifiedProbeCandidate(
                id=f"P{i}",
                goal=f"Goal {i}",
                expected_value="high",
                reason=f"reason {i}",
            )
            for i in range(5)
        ]

        # LLM returns 5 probes, but cap should reduce to 2
        fake_output = DomainRouterOutput(
            assignments=[
                DomainAssignment(
                    domain_id="example",
                    domain_display_name="Example Domain",
                    probes=[
                        DomainProbe(
                            probe_candidate_id=f"P{i}",
                            domain_id="example",
                            scoped_question=f"Scoped question {i}",
                            expected_value="high",
                            reason=f"reason {i}",
                        )
                        for i in range(5)
                    ],
                ),
            ]
        )

        budget = ProbeBudgetConfig(max_probes_per_round=2)
        chat_model = FakeStructuredChatModel({DomainRouterOutput: [fake_output]})
        service = DomainRouterService(chat_model=chat_model, probe_budget=budget)

        result = service.run(
            DomainRouterInput(
                consultant_plan=_make_consultant_output(*probes),
                available_domains=[sample_domain_config],
                asked_questions=[],
            )
        )

        total_probes = sum(len(a.probes) for a in result.assignments)
        assert total_probes <= 2

    def test_deduplicates_asked_questions(self, sample_domain_config):
        """A probe whose scoped_question matches an asked question is dropped."""
        probe = UnifiedProbeCandidate(
            id="P1",
            goal="Check brand health",
            expected_value="high",
            reason="core",
        )

        duplicate_q = "What is the brand health of Budweiser in Brazil in Q1 2026?"

        fake_output = DomainRouterOutput(
            assignments=[
                DomainAssignment(
                    domain_id="example",
                    domain_display_name="Example Domain",
                    probes=[
                        DomainProbe(
                            probe_candidate_id="P1",
                            domain_id="example",
                            scoped_question=duplicate_q,
                            expected_value="high",
                            reason="matches brand health",
                        ),
                    ],
                ),
            ]
        )

        chat_model = FakeStructuredChatModel({DomainRouterOutput: [fake_output]})
        service = DomainRouterService(chat_model=chat_model)

        result = service.run(
            DomainRouterInput(
                consultant_plan=_make_consultant_output(probe),
                available_domains=[sample_domain_config],
                asked_questions=[duplicate_q],
            )
        )

        # The duplicate should be dropped, leaving empty assignments
        total_probes = sum(len(a.probes) for a in result.assignments)
        assert total_probes == 0

    def test_empty_candidates_returns_empty(self, sample_domain_config):
        """No probe candidates → empty assignments."""
        chat_model = FakeStructuredChatModel({})
        service = DomainRouterService(chat_model=chat_model)

        result = service.run(
            DomainRouterInput(
                consultant_plan=_make_consultant_output(),
                available_domains=[sample_domain_config],
                asked_questions=[],
            )
        )

        assert result.assignments == []
