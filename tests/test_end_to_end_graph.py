from langgraph.graph import END, START, StateGraph

from ic_agent.config.probe_budget import ProbeBudgetConfig
from ic_agent.graph.edges import route_after_decision_engine
from ic_agent.graph.nodes import (
    make_decision_consultant_node,
    make_decision_engine_node,
    make_execution_node,
    make_planner_consultant_node,
    make_planner_node,
    make_similar_plan_node,
    make_synthesis_node,
)
from ic_agent.models.decision_consultant import DecisionConsultantOutput, RemainingGap
from ic_agent.models.decision_engine import GapRecommendation
from ic_agent.models.planner import PlannerUsecaseAssignments, ProbeUsecaseAssignment, QuestionItem
from ic_agent.models.planner_consultant import Hypothesis, PlannerConsultantOutput, ProbeCandidate
from ic_agent.models.state import AgentState
from ic_agent.models.synthesizer import SynthesizerOutput
from ic_agent.services.decision_consultant_service import DecisionConsultantService
from ic_agent.services.decision_engine_service import DecisionEngineService
from ic_agent.services.planner_consultant_service import PlannerConsultantService
from ic_agent.services.planner_service import PlannerService
from ic_agent.services.retrieval_service import MockRetrievalClient, RetrievalService
from ic_agent.services.similar_plan_service import SimilarPlanService
from ic_agent.services.synthesizer_service import SynthesizerService
from tests.conftest import FakeStructuredChatModel

_SYNTHESIS_MARKDOWN = """## Summary
Revenue declined mainly due to pricing pressure in East China.

## Key Findings
- Pricing was the dominant driver of the revenue decline.

## Evidence
- Revenue trend was down in East China.
- Volume trend was roughly flat in East China.

## Recommendations
- Investigate pricing strategy and competitor activity in East China.

## Confidence
Moderate confidence based on the available evidence.

## Remaining Unknowns
- Impact of competitor promotions is unclear.
"""


def _build_test_app(
    tmp_path,
    sample_domain_config,
    sample_score_fusion_weights,
    stub_embedding_backend,
    probe_budget,
):
    consultant_plan = PlannerConsultantOutput(
        objective="Investigate the East China revenue decline",
        hypotheses=[Hypothesis(id="H1", description="Pricing pressure reduced revenue")],
        probe_candidates=[
            ProbeCandidate(
                id="PC1",
                goal="Check revenue trend in East China",
                expected_value="high",
                reason="r",
            ),
            ProbeCandidate(
                id="PC2",
                goal="Check volume trend in East China",
                expected_value="medium",
                reason="r",
            ),
        ],
        success_criteria="Top driver of the decline is identified",
        open_questions=[],
    )
    decision_consultant_output = DecisionConsultantOutput(
        relevant_probes=[],
        irrelevant_probes=[],
        remaining_gaps=[RemainingGap(description="pricing contribution", category="open")],
        new_hypotheses=[],
        confidence=0.0,
    )
    gap_recommendation = GapRecommendation(
        recommended_next_gap="pricing contribution", reason="Marginal value too low to continue."
    )
    synthesizer_output = SynthesizerOutput(markdown=_SYNTHESIS_MARKDOWN, confidence=0.5)

    similar_plan_service = SimilarPlanService(
        corpus_path="corpus/similar_plans.yaml",
        score_fusion_weights=sample_score_fusion_weights,
        embedding_backend=stub_embedding_backend,
        cache_dir=tmp_path,
    )
    planner_consultant_service = PlannerConsultantService(
        FakeStructuredChatModel({PlannerConsultantOutput: [consultant_plan]})
    )
    usecase_assignments = PlannerUsecaseAssignments(
        assignments=[
            ProbeUsecaseAssignment(
                probe_candidate_id="PC1",
                questions=[QuestionItem(text="q1")],
                usecase="brand_guidance",
                reason="r",
            ),
            ProbeUsecaseAssignment(
                probe_candidate_id="PC2",
                questions=[QuestionItem(text="q2")],
                usecase="category",
                reason="r",
            ),
        ]
    )
    planner_service = PlannerService(
        sample_domain_config,
        usecase_docs={"brand_guidance": "bg doc", "category": "category doc"},
        chat_model=FakeStructuredChatModel({PlannerUsecaseAssignments: [usecase_assignments]}),
        probe_budget=probe_budget,
    )
    retrieval_service = RetrievalService(MockRetrievalClient())
    decision_consultant_service = DecisionConsultantService(
        sample_domain_config,
        FakeStructuredChatModel({DecisionConsultantOutput: [decision_consultant_output]}),
    )
    decision_engine_service = DecisionEngineService(
        sample_domain_config,
        FakeStructuredChatModel({GapRecommendation: [gap_recommendation]}),
    )
    synthesizer_service = SynthesizerService(
        sample_domain_config,
        FakeStructuredChatModel({SynthesizerOutput: [synthesizer_output]}),
    )

    graph = StateGraph(AgentState)
    graph.add_node("similar_plan", make_similar_plan_node(similar_plan_service))
    graph.add_node("planner_consultant", make_planner_consultant_node(planner_consultant_service))
    graph.add_node("planner", make_planner_node(planner_service))
    graph.add_node("execution", make_execution_node(retrieval_service))
    graph.add_node(
        "decision_consultant", make_decision_consultant_node(decision_consultant_service)
    )
    graph.add_node(
        "decision_engine", make_decision_engine_node(decision_engine_service, probe_budget)
    )
    graph.add_node("synthesis", make_synthesis_node(synthesizer_service))

    graph.add_edge(START, "similar_plan")
    graph.add_edge("similar_plan", "planner_consultant")
    graph.add_edge("planner_consultant", "planner")
    graph.add_edge("planner", "execution")
    graph.add_edge("execution", "decision_consultant")
    graph.add_edge("decision_consultant", "decision_engine")
    graph.add_conditional_edges(
        "decision_engine",
        route_after_decision_engine,
        {"continue": "planner_consultant", "stop": "synthesis"},
    )
    graph.add_edge("synthesis", END)

    return graph.compile()


def test_graph_terminates_with_synthesis(
    tmp_path, sample_domain_config, sample_score_fusion_weights, stub_embedding_backend
):
    probe_budget = ProbeBudgetConfig(max_rounds=2, max_probes_per_round=2, max_total_probes=4)
    app = _build_test_app(
        tmp_path,
        sample_domain_config,
        sample_score_fusion_weights,
        stub_embedding_backend,
        probe_budget,
    )

    initial_state: AgentState = {
        "query": "Why did revenue decline in East China during Q1?",
        "domain_config": sample_domain_config,
        "evidence_ledger": [],
        "rounds_completed": 0,
        "probes_completed_this_round": 0,
        "total_probes_completed": 0,
        "remaining_gaps": [],
        "confidence": 0.0,
    }

    final_state = app.invoke(initial_state, config={"recursion_limit": 50})

    assert final_state["total_probes_completed"] <= probe_budget.max_total_probes
    assert final_state["rounds_completed"] <= probe_budget.max_rounds
    assert final_state["decision_engine_output"].continue_ is False

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

    assert all(
        entry.result.startswith("Mock answer to: ") for entry in final_state["evidence_ledger"]
    )
