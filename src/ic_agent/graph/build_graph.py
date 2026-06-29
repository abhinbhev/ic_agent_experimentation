"""Builds the compiled LangGraph application.

Graph shape (see docs/archetecture.md "LangGraph Implementation Notes"):

    START -> similar_plan -> planner_consultant -> planner -> execution
          -> decision_consultant -> decision_engine
          --(continue)--> planner_consultant
          --(stop)-------> synthesis -> END
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ic_agent.config.corpus_paths import resolve_domain_corpus_path
from ic_agent.config.probe_budget import load_probe_budget_settings
from ic_agent.config.settings import Settings, get_settings
from ic_agent.config.usecase_docs import (
    load_question_format_doc,
    load_schema_doc,
    load_usecase_docs,
)
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
from ic_agent.models.domain import DomainConfig
from ic_agent.models.state import AgentState
from ic_agent.services.decision_consultant_service import DecisionConsultantService
from ic_agent.services.decision_engine_service import DecisionEngineService
from ic_agent.services.embeddings import get_embedding_backend
from ic_agent.services.llm_factory import get_chat_model
from ic_agent.services.planner_consultant_service import PlannerConsultantService
from ic_agent.services.planner_service import PlannerService
from ic_agent.services.retrieval_service import RetrievalService, get_retrieval_client
from ic_agent.services.similar_plan_service import SimilarPlanService
from ic_agent.services.synthesizer_service import SynthesizerService


def build_app(domain_config: DomainConfig, settings: Settings | None = None) -> CompiledStateGraph:
    settings = settings or get_settings()
    budget_settings = load_probe_budget_settings(settings.probe_budget_path)

    similar_plan_service = SimilarPlanService(
        corpus_path=resolve_domain_corpus_path(domain_config.domain_id, settings.corpus_path),
        score_fusion_weights=budget_settings.score_fusion,
        embedding_backend=get_embedding_backend(settings),
    )
    planner_consultant_service = PlannerConsultantService(get_chat_model(settings))
    usecase_docs = load_usecase_docs(
        domain_config.domain_id, settings.usecase_docs_dir, domain_config.primary_usecase
    )
    schema_doc = load_schema_doc(domain_config.domain_id, settings.usecase_docs_dir)
    question_format_doc = load_question_format_doc(
        domain_config.domain_id, settings.usecase_docs_dir
    )
    planner_service = PlannerService(
        domain_config,
        usecase_docs,
        get_chat_model(settings),
        probe_budget=budget_settings.probe_budget,
        schema_doc=schema_doc,
        question_format_doc=question_format_doc,
    )
    # Build the retrieval client from the explicit settings so callers
    # can override ``retrieval_mode`` (e.g. flipping to "mock" from the UI).
    retrieval_service = RetrievalService(client=get_retrieval_client(settings))
    decision_consultant_service = DecisionConsultantService(domain_config, get_chat_model(settings))
    decision_engine_service = DecisionEngineService(
        domain_config, get_chat_model(settings), weights=budget_settings.incremental_value_weights
    )
    synthesizer_service = SynthesizerService(
        domain_config,
        get_chat_model(settings),
        usecase_docs=usecase_docs,
        schema_doc=schema_doc,
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
        "decision_engine",
        make_decision_engine_node(decision_engine_service, budget_settings.probe_budget),
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
