"""Loads domain configuration from YAML files.

Each domain is a self-contained YAML file under ``config/domains/``. This
is the only thing that needs to change to adapt the system to a new
domain -- core logic and prompts remain untouched.
"""

from pathlib import Path

import yaml

from ic_agent.models.domain import DomainConfig


def load_domain_config(domain_id: str, base_dir: str | Path = "config/domains") -> DomainConfig:
    """Load ``<base_dir>/<domain_id>.yaml`` into a ``DomainConfig``."""
    path = Path(base_dir) / f"{domain_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No domain config found at {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return DomainConfig.model_validate(data)
