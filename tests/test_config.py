import pytest

from ic_agent.config.probe_budget import IncrementalValueWeights, load_probe_budget_settings
from ic_agent.config.settings import Settings


def test_settings_defaults_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-5.4"
    assert settings.embedding_backend == "openai"
    assert settings.litellm_base_url is None
    assert settings.litellm_api_key is None


def test_litellm_base_url_and_api_key_are_normalized():
    settings = Settings(
        _env_file=None,
        AZURE_OPENAI_ENDPOINT_LITELLM="https://example.com/",
        AZURE_OPENAI_API_KEY_LITELLM="Bearer sk-abc123",
    )

    assert settings.litellm_base_url == "https://example.com/v1"
    assert settings.litellm_api_key == "sk-abc123"


def test_load_probe_budget_settings_from_yaml():
    settings = load_probe_budget_settings("config/probe_budget.yaml")

    assert settings.probe_budget.max_rounds == 5
    assert settings.probe_budget.max_probes_per_round == 6
    assert settings.probe_budget.max_total_probes == 20

    assert settings.score_fusion.bm25_weight == 0.5
    assert settings.score_fusion.embedding_weight == 0.5
    assert settings.score_fusion.fusion_method == "weighted_sum"

    assert settings.incremental_value_weights.stop_threshold == 0.35


def test_load_probe_budget_settings_missing_file_uses_defaults():
    settings = load_probe_budget_settings("config/does_not_exist.yaml")

    assert settings.probe_budget.max_rounds == 5
    assert settings.incremental_value_weights.evidence_coverage == 0.30


def test_incremental_value_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        IncrementalValueWeights(
            evidence_coverage=0.5,
            confidence=0.5,
            remaining_gaps=0.5,
            alternative_hypotheses=0.5,
            probe_cost=0.5,
        )
