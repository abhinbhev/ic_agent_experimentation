"""Tests for unified domain LLM services.

Uses FakeStructuredChatModel — no API key required.
"""

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_engine import DecisionEngineOutput, GapRecommendation
from ic_agent.models.synthesizer import SynthesizerOutput
from tests.conftest import FakeStructuredChatModel
from unified_domain.models.decision_consultant import (
    UnifiedDecisionConsultantInput,
    UnifiedDecisionConsultantOutput,
    UnifiedRemainingGap,
)
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.models.planner_consultant import (
    UnifiedHypothesis,
    UnifiedPlannerConsultantInput,
    UnifiedPlannerConsultantOutput,
    UnifiedProbeCandidate,
)
from unified_domain.services.decision_consultant_service import (
    UnifiedDecisionConsultantService,
)
from unified_domain.services.decision_engine_service import (
    UnifiedDecisionEngineInput,
    UnifiedDecisionEngineService,
)
from unified_domain.services.planner_consultant_service import (
    UnifiedPlannerConsultantService,
)
from unified_domain.services.synthesizer_service import (
    UnifiedSynthesizerInput,
    UnifiedSynthesizerService,
)


def test_planner_consultant_produces_output():
    fake_output = UnifiedPlannerConsultantOutput(
        objective="Investigate brand performance across domains",
        hypotheses=[
            UnifiedHypothesis(
                id="H1",
                description="Brand health is declining",
                status="open",
            ),
        ],
        probe_candidates=[
            UnifiedProbeCandidate(
                id="P1",
                goal="What is the brand's overall health trajectory?",
                expected_value="high",
                reason="Core question",
            ),
            UnifiedProbeCandidate(
                id="P2",
                goal="How has consumer perception shifted?",
                expected_value="medium",
                reason="Supports H1",
            ),
        ],
        success_criteria="Brand health trajectory established with evidence",
        open_questions=[],
    )

    model = FakeStructuredChatModel({UnifiedPlannerConsultantOutput: [fake_output]})
    service = UnifiedPlannerConsultantService(chat_model=model)

    result = service.run(
        UnifiedPlannerConsultantInput(
            query="How is Brahma performing in Brazil?",
            domain_knowledge_doc="Overview of brand and category data.",
        )
    )

    assert isinstance(result, UnifiedPlannerConsultantOutput)
    assert len(result.probe_candidates) == 2
    assert result.probe_candidates[0].id == "P1"
    assert len(result.hypotheses) == 1


def test_decision_consultant_evaluates_evidence():
    fake_output = UnifiedDecisionConsultantOutput(
        relevant_probes=["P-aaa"],
        irrelevant_probes=["P-bbb"],
        remaining_gaps=[
            UnifiedRemainingGap(
                description="Consumer perception data not gathered",
                category="open",
            ),
            UnifiedRemainingGap(
                description="Brand health trend established",
                category="closed",
            ),
            UnifiedRemainingGap(
                description="Consumption vs perception alignment unclear",
                category="partial",
            ),
        ],
        new_hypotheses=[],
        confidence=0.55,
    )

    model = FakeStructuredChatModel({UnifiedDecisionConsultantOutput: [fake_output]})
    service = UnifiedDecisionConsultantService(chat_model=model)

    ledger = [
        UnifiedEvidenceLedgerEntry(
            probe_id="P-aaa",
            question="What is the brand health?",
            source_domain_id="brand_guidance",
            result="Power: 50",
            created_at="2026-01-01T00:00:00Z",
            round_index=0,
        ),
        UnifiedEvidenceLedgerEntry(
            probe_id="P-bbb",
            question="Unrelated question",
            source_domain_id="category",
            result="No data",
            created_at="2026-01-01T00:01:00Z",
            round_index=0,
        ),
    ]

    result = service.run(
        UnifiedDecisionConsultantInput(
            query="How is Brahma performing?",
            ledger=ledger,
        )
    )

    assert isinstance(result, UnifiedDecisionConsultantOutput)
    assert result.confidence == 0.55
    assert len(result.remaining_gaps) == 3
    # 2 unresolved: 1 open + 1 partial
    unresolved = [
        g for g in result.remaining_gaps if g.category in {"open", "partial", "conflicting"}
    ]
    assert len(unresolved) == 2


def test_decision_engine_stops_on_max_rounds():
    dc_output = UnifiedDecisionConsultantOutput(
        relevant_probes=["P-aaa"],
        irrelevant_probes=[],
        remaining_gaps=[
            UnifiedRemainingGap(
                description="Some gap",
                category="open",
            ),
        ],
        new_hypotheses=[],
        confidence=0.5,
    )

    # The LLM call for gap recommendation won't be reached when
    # max_rounds is hit, but we provide a fake just in case.
    fake_gap_rec = GapRecommendation(
        recommended_next_gap=None,
        reason="Budget exhausted",
    )
    model = FakeStructuredChatModel({GapRecommendation: [fake_gap_rec]})
    service = UnifiedDecisionEngineService(chat_model=model)

    input_data = UnifiedDecisionEngineInput(
        ledger=[
            UnifiedEvidenceLedgerEntry(
                probe_id="P-aaa",
                question="Some question",
                source_domain_id="brand_guidance",
                result="Some answer",
                created_at="2026-01-01T00:00:00Z",
                round_index=0,
            ),
        ],
        decision_consultant_output=dc_output,
        rounds_completed=5,
        probes_completed_this_round=2,
        total_probes_completed=10,
        probe_budget=ProbeBudgetConfig(max_rounds=5, max_probes_per_round=5, max_total_probes=20),
    )

    result = service.run(input_data)

    assert isinstance(result, DecisionEngineOutput)
    assert result.continue_ is False
    assert result.stop_reason == "max_rounds_reached"


def test_synthesizer_produces_markdown():
    markdown = (
        "## Summary\nBrand is stable.\n\n"
        "## Key Findings\n- Power score: 50\n\n"
        "## Evidence\n- Power from brand domain\n\n"
        "## Recommendations\n- Invest in awareness\n\n"
        "## Confidence\nModerate confidence.\n\n"
        "## Remaining Unknowns\n- Consumer perception gaps\n"
    )
    fake_output = SynthesizerOutput(markdown=markdown, confidence=0.6)

    model = FakeStructuredChatModel({SynthesizerOutput: [fake_output]})
    service = UnifiedSynthesizerService(chat_model=model)

    input_data = UnifiedSynthesizerInput(
        query="How is Brahma performing?",
        ledger=[
            UnifiedEvidenceLedgerEntry(
                probe_id="P-aaa",
                question="What is brand health?",
                source_domain_id="brand_guidance",
                result="Power: 50",
                created_at="2026-01-01T00:00:00Z",
                round_index=0,
            ),
        ],
        stop_reason="all_major_gaps_closed",
        domain_knowledge_doc="Brand and category overview.",
    )

    result = service.run(input_data)

    assert isinstance(result, SynthesizerOutput)
    assert result.confidence == 0.6
    for heading in [
        "## Summary",
        "## Key Findings",
        "## Evidence",
        "## Recommendations",
        "## Confidence",
        "## Remaining Unknowns",
    ]:
        assert heading in result.markdown
