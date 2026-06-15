import pytest

from ic_agent.config.domain_loader import load_domain_config


def test_load_example_domain_config():
    domain = load_domain_config("example")

    assert domain.domain_id == "example"
    assert {d.name for d in domain.datasets} >= {"Sales", "Revenue"}
    assert {m.name for m in domain.metrics} >= {"Volume", "Revenue"}
    assert {dim.name for dim in domain.dimensions} >= {"Brand", "Region"}


def test_load_domain_config_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_domain_config("does_not_exist")
