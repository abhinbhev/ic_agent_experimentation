from ic_agent.config.domain_loader import load_domain_config
from ic_agent.models.similar_plan import SimilarPlanQuery
from ic_agent.services.similar_plan_service import SimilarPlanService


def test_search_falls_back_to_full_corpus_when_no_dataset_family_match(
    tmp_path, sample_domain_config, sample_score_fusion_weights, stub_embedding_backend
):
    """The corpus currently only has a "Brand Guidance" archetype. A domain
    with no overlapping dataset family still gets it back via the
    metadata filter's full-corpus fallback."""
    service = SimilarPlanService(
        corpus_path="corpus/similar_plans.yaml",
        score_fusion_weights=sample_score_fusion_weights,
        embedding_backend=stub_embedding_backend,
        top_k=3,
        cache_dir=tmp_path,
    )

    result = service.search(
        SimilarPlanQuery(
            user_query="Why did revenue decline in East China during Q1?",
            domain_context=sample_domain_config,
        )
    )

    assert result.matched_patterns
    top = result.matched_patterns[0]
    assert top.pattern_id == "brand_country_period_performance_bg"
    assert 0.0 <= top.confidence <= 1.0
    assert top.probe_strategy == [
        "change in equity",
        "factors affecting equity",
        "perceptions of the brand",
        "consumption",
        "demographic insights",
    ]


def test_search_matches_brand_guidance_domain_via_dataset_family(
    tmp_path, sample_score_fusion_weights, stub_embedding_backend
):
    domain_config = load_domain_config("gai_copilot_marketing_brand_guidance_ghq")
    service = SimilarPlanService(
        corpus_path="corpus/similar_plans.yaml",
        score_fusion_weights=sample_score_fusion_weights,
        embedding_backend=stub_embedding_backend,
        top_k=3,
        cache_dir=tmp_path,
    )

    result = service.search(
        SimilarPlanQuery(
            user_query="How is Brahma performing in Brazil this quarter?",
            domain_context=domain_config,
        )
    )

    assert result.matched_patterns
    top = result.matched_patterns[0]
    assert top.pattern_id == "brand_country_period_performance_bg"


def test_search_empty_corpus_returns_no_matches(
    tmp_path, sample_domain_config, sample_score_fusion_weights, stub_embedding_backend
):
    empty_corpus = tmp_path / "empty.yaml"
    empty_corpus.write_text("[]", encoding="utf-8")

    service = SimilarPlanService(
        corpus_path=empty_corpus,
        score_fusion_weights=sample_score_fusion_weights,
        embedding_backend=stub_embedding_backend,
    )

    result = service.search(
        SimilarPlanQuery(user_query="anything", domain_context=sample_domain_config)
    )

    assert result.matched_patterns == []
