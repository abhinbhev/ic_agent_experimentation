"""Builds the compiled LangGraph application for the unified (super-agent) pipeline.

Graph shape:

    START → similar_plan → planner_consultant → domain_router → domain_execution
          → decision_consultant → decision_engine
          ──(continue)──→ planner_consultant
          ──(stop)──────→ synthesis → END
"""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ic_agent.config.corpus_paths import resolve_unified_corpus_path
from ic_agent.config.probe_budget import load_probe_budget_settings
from ic_agent.config.settings import Settings, get_settings
from ic_agent.models.domain import DomainConfig
from ic_agent.services.embeddings import get_embedding_backend
from ic_agent.services.llm_factory import get_chat_model
from ic_agent.services.similar_plan_service import SimilarPlanService
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
from unified_domain.models.state import UnifiedAgentState
from unified_domain.services.decision_consultant_service import (
    UnifiedDecisionConsultantService,
)
from unified_domain.services.decision_engine_service import (
    UnifiedDecisionEngineService,
)
from unified_domain.services.domain_agent_executor import DomainAgentExecutor
from unified_domain.services.domain_router_service import DomainRouterService
from unified_domain.services.planner_consultant_service import (
    UnifiedPlannerConsultantService,
)
from unified_domain.services.synthesizer_service import UnifiedSynthesizerService

logger = logging.getLogger(__name__)


def build_unified_app(
    available_domains: list[DomainConfig],
    settings: Settings | None = None,
    domain_knowledge_doc: str = "",
    budget_path: str = "config/unified_probe_budget.yaml",
) -> CompiledStateGraph:
    settings = settings or get_settings()
    budget_settings = load_probe_budget_settings(budget_path)

    similar_plan_service = SimilarPlanService(
        corpus_path=resolve_unified_corpus_path(settings.corpus_path),
        score_fusion_weights=budget_settings.score_fusion,
        embedding_backend=get_embedding_backend(settings),
    )
    planner_consultant_service = UnifiedPlannerConsultantService(get_chat_model(settings))
    domain_router_service = DomainRouterService(
        get_chat_model(settings), probe_budget=budget_settings.probe_budget
    )
    domain_agent_executor = DomainAgentExecutor(settings)
    decision_consultant_service = UnifiedDecisionConsultantService(get_chat_model(settings))
    decision_engine_service = UnifiedDecisionEngineService(
        get_chat_model(settings), weights=budget_settings.incremental_value_weights
    )
    synthesizer_service = UnifiedSynthesizerService(
        get_chat_model(settings), domain_knowledge_doc=domain_knowledge_doc
    )

    graph = StateGraph(UnifiedAgentState)

    graph.add_node("similar_plan", make_similar_plan_node(similar_plan_service))
    graph.add_node(
        "planner_consultant",
        make_planner_consultant_node(planner_consultant_service),
    )
    graph.add_node("domain_router", make_domain_router_node(domain_router_service))
    graph.add_node("domain_execution", make_domain_execution_node(domain_agent_executor))
    graph.add_node(
        "decision_consultant",
        make_decision_consultant_node(decision_consultant_service),
    )
    graph.add_node(
        "decision_engine",
        make_decision_engine_node(decision_engine_service, budget_settings.probe_budget),
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

    logger.info("Built unified graph with %d available domains", len(available_domains))
    return graph.compile()
