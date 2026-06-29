"""End-to-end test for the unified (super-agent) graph.

Follows the same pattern as ``tests/test_end_to_end_graph.py``:
builds the full graph manually with fake services and asserts that
it terminates correctly with a synthesized answer.
"""

from langgraph.graph import END, START, StateGraph

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.models.decision_engine import GapRecommendation
from ic_agent.models.synthesizer import SynthesizerOutput
from ic_agent.services.similar_plan_service import SimilarPlanService
from tests.conftest import FakeStructuredChatModel
from unified_domain.graph.edges import route_after_decision_engine
from unified_domain.graph.nodes import (
    make_decision_consultant_node,
    make_decision_engine_node,
    make_domain_execution_node,
    make_domain_router_node,
    make_planner_consultant_node,
    make_similar_plan_node,
    make_synthesis_node,
)
from unified_domain.models.decision_consultant import (
    UnifiedDecisionConsultantOutput,
    UnifiedRemainingGap,
)
from unified_domain.models.domain_router import (
    DomainAssignment,
    DomainProbe,
    DomainRouterOutput,
)
from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
from unified_domain.models.planner_consultant import (
    UnifiedHypothesis,
    UnifiedPlannerConsultantOutput,
    UnifiedProbeCandidate,
)
from unified_domain.models.state import UnifiedAgentState
from unified_domain.services.decision_consultant_service import (
    UnifiedDecisionConsultantService,
)
from unified_domain.services.decision_engine_service import (
    UnifiedDecisionEngineService,
)
from unified_domain.services.domain_router_service import DomainRouterService
from unified_domain.services.planner_consultant_service import (
    UnifiedPlannerConsultantService,
)
from unified_domain.services.synthesizer_service import UnifiedSynthesizerService

# ---------------------------------------------------------------------------
# Canned outputs
# ---------------------------------------------------------------------------

_CONSULTANT_PLAN = UnifiedPlannerConsultantOutput(
    objective="Investigate brand health across domains",
    hypotheses=[
        UnifiedHypothesis(id="H1", description="Brand equity is declining"),
        UnifiedHypothesis(id="H2", description="Category consumption is shifting"),
    ],
    probe_candidates=[
        UnifiedProbeCandidate(
            id="PC1",
            goal="How did brand equity change recently?",
            expected_value="high",
            reason="Direct measure of brand health",
        ),
        UnifiedProbeCandidate(
            id="PC2",
            goal="What are consumption trends in the category?",
            expected_value="medium",
            reason="Contextualises brand performance",
        ),
    ],
    success_criteria="Top drivers of brand health identified",
    open_questions=[],
)

_DOMAIN_ROUTER_OUTPUT = DomainRouterOutput(
    assignments=[
        DomainAssignment(
            domain_id="brand_guidance_domain",
            domain_display_name="Brand Guidance",
            probes=[
                DomainProbe(
                    probe_candidate_id="PC1",
                    domain_id="brand_guidance_domain",
                    scoped_question="What is the power of Brahma in Brazil in Q1 2026?",
                    expected_value="high",
                    reason="Maps to brand equity KPI",
                ),
            ],
        ),
        DomainAssignment(
            domain_id="category_domain",
            domain_display_name="Category",
            probes=[
                DomainProbe(
                    probe_candidate_id="PC2",
                    domain_id="category_domain",
                    scoped_question="What is consumption past seven days for Beer in Brazil?",
                    expected_value="medium",
                    reason="Consumption trend for category",
                ),
            ],
        ),
    ]
)

_DECISION_CONSULTANT_OUTPUT = UnifiedDecisionConsultantOutput(
    relevant_probes=["PC1", "PC2"],
    irrelevant_probes=[],
    remaining_gaps=[
        UnifiedRemainingGap(description="pricing contribution", category="open"),
    ],
    new_hypotheses=[],
    confidence=0.0,
)

_GAP_RECOMMENDATION = GapRecommendation(
    recommended_next_gap="pricing contribution",
    reason="Marginal value too low to continue.",
)

_SYNTHESIS_MARKDOWN = """## Summary
Brand health is stable but consumption is shifting.

## Key Findings
- Brand equity remained flat in Q1 2026.
- Category consumption declined marginally.

## Evidence
- Power of Brahma was 42 in Q1 2026.
- Consumption past seven days for Beer was 18%.

## Recommendations
- Monitor pricing strategy.

## Confidence
Moderate confidence based on available evidence.

## Remaining Unknowns
- Impact of competitor activity is unclear.
"""

_SYNTHESIZER_OUTPUT = SynthesizerOutput(markdown=_SYNTHESIS_MARKDOWN, confidence=0.5)


# ---------------------------------------------------------------------------
# Fake domain agent executor
# ---------------------------------------------------------------------------


class FakeDomainAgentExecutor:
    """Returns canned UnifiedEvidenceLedgerEntry for each probe."""

    def execute_sync(self, assignments, round_index=0, *, event_bus=None):
        entries = []
        for assignment in assignments:
            for probe in assignment.probes:
                entries.append(
                    UnifiedEvidenceLedgerEntry(
                        probe_id=f"fake-{probe.probe_candidate_id}",
                        question=probe.scoped_question,
                        source_domain_id=assignment.domain_id,
                        result=f"Mock domain report for: {probe.scoped_question}",
                        sub_evidence=[],
                        created_at="2026-01-01T00:00:00Z",
                        round_index=round_index,
                    )
                )
        return entries


# ---------------------------------------------------------------------------
# Graph builder helper
# ---------------------------------------------------------------------------


def _build_test_app(
    tmp_path,
    sample_domain_config,
    sample_score_fusion_weights,
    stub_embedding_backend,
    probe_budget,
):
    similar_plan_service = SimilarPlanService(
        corpus_path="corpus/similar_plans.yaml",
        score_fusion_weights=sample_score_fusion_weights,
        embedding_backend=stub_embedding_backend,
        cache_dir=tmp_path,
    )
    planner_consultant_service = UnifiedPlannerConsultantService(
        FakeStructuredChatModel({UnifiedPlannerConsultantOutput: [_CONSULTANT_PLAN]})
    )
    domain_router_service = DomainRouterService(
        FakeStructuredChatModel({DomainRouterOutput: [_DOMAIN_ROUTER_OUTPUT]}),
        probe_budget=probe_budget,
    )
    fake_executor = FakeDomainAgentExecutor()
    decision_consultant_service = UnifiedDecisionConsultantService(
        FakeStructuredChatModel({UnifiedDecisionConsultantOutput: [_DECISION_CONSULTANT_OUTPUT]})
    )
    decision_engine_service = UnifiedDecisionEngineService(
        FakeStructuredChatModel({GapRecommendation: [_GAP_RECOMMENDATION]}),
    )
    synthesizer_service = UnifiedSynthesizerService(
        FakeStructuredChatModel({SynthesizerOutput: [_SYNTHESIZER_OUTPUT]}),
    )

    graph = StateGraph(UnifiedAgentState)

    graph.add_node("similar_plan", make_similar_plan_node(similar_plan_service))
    graph.add_node(
        "planner_consultant",
        make_planner_consultant_node(planner_consultant_service),
    )
    graph.add_node("domain_router", make_domain_router_node(domain_router_service))
    graph.add_node("domain_execution", make_domain_execution_node(fake_executor))
    graph.add_node(
        "decision_consultant",
        make_decision_consultant_node(decision_consultant_service),
    )
    graph.add_node(
        "decision_engine",
        make_decision_engine_node(decision_engine_service, probe_budget),
    )
    graph.add_node("synthesis", make_synthesis_node(synthesizer_service))

    graph.add_edge(START, "similar_plan")
    graph.add_edge("similar_plan", "planner_consultant")
    graph.add_edge("planner_consultant", "domain_router")
    graph.add_edge("domain_router", "domain_execution")
    graph.add_edge("domain_execution", "decision_consultant")
    graph.add_edge("decision_consultant", "decision_engine")
    graph.add_conditional_edges(
        "decision_engine",
        route_after_decision_engine,
        {"continue": "planner_consultant", "stop": "synthesis"},
    )
    graph.add_edge("synthesis", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unified_graph_terminates_with_synthesis(
    tmp_path, sample_domain_config, sample_score_fusion_weights, stub_embedding_backend
):
    probe_budget = ProbeBudgetConfig(max_rounds=2, max_probes_per_round=3, max_total_probes=6)
    app = _build_test_app(
        tmp_path,
        sample_domain_config,
        sample_score_fusion_weights,
        stub_embedding_backend,
        probe_budget,
    )

    initial_state: UnifiedAgentState = {
        "query": "How is brand health evolving across domains?",
        "available_domains": [sample_domain_config],
        "domain_knowledge_doc": "",
        "evidence_ledger": [],
        "rounds_completed": 0,
        "probes_completed_this_round": 0,
        "total_probes_completed": 0,
        "remaining_gaps": [],
        "confidence": 0.0,
    }

    final_state = app.invoke(initial_state, config={"recursion_limit": 50})

    # Budget limits respected
    assert final_state["total_probes_completed"] <= probe_budget.max_total_probes
    assert final_state["rounds_completed"] <= probe_budget.max_rounds

    # Graph terminated (decision engine said stop)
    assert final_state["decision_engine_output"].continue_ is False

    # Synthesis produced all 6 required sections
    final_answer = final_state["final_answer"]
    for header in (
        "## Summary",
        "## Key Findings",
        "## Evidence",
        "## Recommendations",
        "## Confidence",
        "## Remaining Unknowns",
    ):
        assert header in final_answer.markdown

    # Evidence ledger entries have source_domain_id set
    for entry in final_state["evidence_ledger"]:
        assert entry.source_domain_id, f"Entry {entry.probe_id} missing source_domain_id"
