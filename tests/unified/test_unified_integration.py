"""Integration tests for the unified domain super-agent.

These tests make real LLM calls and are skipped unless OPENAI_API_KEY is set.
They verify prompt quality, domain routing accuracy, and cross-domain
synthesis coherence.
"""

import pytest

from ic_agent.config.settings import get_settings

_settings = get_settings()
_has_llm_credentials = bool(_settings.openai_api_key) or bool(
    _settings.litellm_base_url and _settings.litellm_api_key
)

_SKIP_REASON = "OPENAI_API_KEY not set — skipping integration tests"
pytestmark = pytest.mark.skipif(
    not _has_llm_credentials,
    reason=_SKIP_REASON,
)


def test_unified_planner_consultant_with_real_llm():
    from pathlib import Path

    from ic_agent.config.domain_loader import load_domain_config
    from ic_agent.services.llm_factory import get_chat_model
    from unified_domain.models.planner_consultant import (
        UnifiedPlannerConsultantInput,
    )
    from unified_domain.services.planner_consultant_service import (
        UnifiedPlannerConsultantService,
    )

    settings = get_settings()
    chat_model = get_chat_model(settings)
    service = UnifiedPlannerConsultantService(chat_model)

    # Load real domains
    domain_dir = Path(settings.domain_config_dir)
    available_domains = [
        load_domain_config(p.stem, base_dir=domain_dir)
        for p in sorted(domain_dir.glob("*.yaml"))
        if p.stem != "example"
    ]

    # Load knowledge doc
    knowledge_doc_path = Path(settings.usecase_docs_dir) / "unified_domain" / "knowledge_doc.md"
    domain_knowledge_doc = (
        knowledge_doc_path.read_text(encoding="utf-8") if knowledge_doc_path.exists() else ""
    )

    input_data = UnifiedPlannerConsultantInput(
        query="How did Brahma perform in Brazil in Q1 2026?",
        available_domains=available_domains,
        domain_knowledge_doc=domain_knowledge_doc,
    )

    output = service.run(input_data)

    assert output.objective
    assert len(output.hypotheses) > 0
    assert len(output.probe_candidates) > 0
    assert output.success_criteria
    # Probe goals should be KPI-agnostic (domain-knowledge-based)
    for pc in output.probe_candidates:
        assert pc.expected_value in ("high", "medium", "low")
        assert pc.goal  # non-empty


def test_domain_router_with_real_llm():
    from pathlib import Path

    from ic_agent.config.domain_loader import load_domain_config
    from ic_agent.config.probe_budget import ProbeBudgetConfig
    from ic_agent.services.llm_factory import get_chat_model
    from unified_domain.models.domain_router import DomainRouterInput
    from unified_domain.models.planner_consultant import (
        UnifiedHypothesis,
        UnifiedPlannerConsultantOutput,
        UnifiedProbeCandidate,
    )
    from unified_domain.services.domain_router_service import DomainRouterService

    settings = get_settings()
    chat_model = get_chat_model(settings)
    budget = ProbeBudgetConfig(max_rounds=2, max_probes_per_round=3, max_total_probes=5)
    service = DomainRouterService(chat_model, budget)

    domain_dir = Path(settings.domain_config_dir)
    available_domains = [
        load_domain_config(p.stem, base_dir=domain_dir)
        for p in sorted(domain_dir.glob("*.yaml"))
        if p.stem != "example"
    ]

    # Create a plan with probes that clearly map to different domains
    plan = UnifiedPlannerConsultantOutput(
        objective="Investigate Brahma's performance in Brazil",
        hypotheses=[UnifiedHypothesis(id="H1", description="Brand health is declining")],
        probe_candidates=[
            UnifiedProbeCandidate(
                id="P1",
                goal="What is Brahma's brand equity position in Brazil in Q1 2026?",
                expected_value="high",
                reason="Brand perception is a key indicator",
            ),
            UnifiedProbeCandidate(
                id="P2",
                goal="How has beer consumption changed in Brazil in Q1 2026?",
                expected_value="high",
                reason="Consumption data complements perception",
            ),
        ],
        success_criteria="Both perception and consumption data obtained",
    )

    input_data = DomainRouterInput(
        consultant_plan=plan,
        available_domains=available_domains,
    )

    output = service.run(input_data)

    assert len(output.assignments) > 0
    # Verify assignments have valid domain ids
    valid_domain_ids = {d.domain_id for d in available_domains}
    for assignment in output.assignments:
        assert assignment.domain_id in valid_domain_ids
        assert len(assignment.probes) > 0
        for probe in assignment.probes:
            assert probe.scoped_question  # self-contained question
            assert probe.domain_id == assignment.domain_id


def test_unified_synthesizer_with_real_llm():
    from pathlib import Path

    from ic_agent.services.llm_factory import get_chat_model
    from unified_domain.models.decision_consultant import (
        UnifiedDecisionConsultantOutput,
        UnifiedRemainingGap,
    )
    from unified_domain.models.evidence import UnifiedEvidenceLedgerEntry
    from unified_domain.services.synthesizer_service import (
        UnifiedSynthesizerInput,
        UnifiedSynthesizerService,
    )

    settings = get_settings()
    chat_model = get_chat_model(settings)

    knowledge_doc_path = Path(settings.usecase_docs_dir) / "unified_domain" / "knowledge_doc.md"
    domain_knowledge_doc = (
        knowledge_doc_path.read_text(encoding="utf-8") if knowledge_doc_path.exists() else ""
    )

    service = UnifiedSynthesizerService(chat_model, domain_knowledge_doc=domain_knowledge_doc)

    # Create mock evidence from two domains
    ledger = [
        UnifiedEvidenceLedgerEntry(
            probe_id="P1",
            question="What is Brahma's brand equity in Brazil in Q1 2026?",
            source_domain_id="gai_copilot_marketing_brand_guidance_ghq",
            result=(
                "Brahma's Power score in Brazil Q1 2026 is 15.2, down from"
                " 16.1 in Q4 2025. Meaningful is at 98 (indexed), Salience"
                " at 112."
            ),
            created_at="2026-01-01T00:00:00Z",
            round_index=0,
        ),
        UnifiedEvidenceLedgerEntry(
            probe_id="P2",
            question="How has beer consumption changed in Brazil in Q1 2026?",
            source_domain_id="gai_copilot_marketing_category_ghq",
            result=(
                "Beer participation in Brazil Q1 2026 is 42.3%, up from"
                " 41.8% in Q4 2025. Occasions per week: 2.1. Servings per"
                " occasion: 1.8."
            ),
            created_at="2026-01-01T00:00:00Z",
            round_index=0,
        ),
    ]

    dc_output = UnifiedDecisionConsultantOutput(
        relevant_probes=["P1", "P2"],
        irrelevant_probes=[],
        remaining_gaps=[
            UnifiedRemainingGap(
                description="Competitive context not explored",
                category="open",
            )
        ],
        confidence=0.6,
    )

    input_data = UnifiedSynthesizerInput(
        query="How did Brahma perform in Brazil in Q1 2026?",
        ledger=ledger,
        decision_consultant_output=dc_output,
        stop_reason="incremental_value_below_threshold",
        domain_knowledge_doc=domain_knowledge_doc,
    )

    output = service.run(input_data)

    # Verify all 6 required sections
    for heading in (
        "## Summary",
        "## Key Findings",
        "## Evidence",
        "## Recommendations",
        "## Confidence",
        "## Remaining Unknowns",
    ):
        assert heading in output.markdown, f"Missing section: {heading}"

    assert 0.0 <= output.confidence <= 1.0
