"""Shared prompt architecture.

Every LLM-backed service is given a ``PromptBundle`` made of:

* ``system_prompt`` -- static across domains, defines purpose, behavior,
  responsibilities and output contract for the service. Lives as a
  ``SYSTEM_PROMPT`` constant in each ``prompts/<service>.py`` module. It
  never contains domain-specific knowledge.
* ``domain_prompt`` -- dynamic business context for the selected domain
  (datasets, metrics, dimensions, business rules, terminology, and any
  per-service guidance). Assembled from:

  1. ``render_default_domain_prompt`` -- a generic catalogue rendered from
     the ``DomainConfig`` fields.
  2. ``DomainConfig.domain_prompt_overrides`` (keyed by service name) --
     optional inline per-service text from the domain's YAML config.
  3. ``prompts/domains/<domain_id>/<service_key>.md`` -- an optional
     per-domain, per-use-case guideline file (see ``load_domain_guideline``),
     created only when a domain/service combination needs guidance beyond
     the generic catalogue.

``PromptBundle.render()`` combines the two into the final system message,
appending the domain prompt under an explicit "DOMAIN GUIDELINES" section so
the model can clearly separate its static behavior/output contract from the
dynamic, domain-specific context for the selected domain.
"""

from pathlib import Path
from types import ModuleType

from pydantic import BaseModel

from ic_agent.models.domain import DomainConfig

DOMAIN_GUIDELINES_HEADER = "DOMAIN GUIDELINES"

_DOMAINS_DIR = Path(__file__).parent / "domains"


class PromptBundle(BaseModel):
    system_prompt: str
    domain_prompt: str = ""

    def render(self) -> str:
        """Combine the static system prompt with the dynamic domain prompt."""
        if not self.domain_prompt:
            return self.system_prompt
        return f"{self.system_prompt}\n\n{DOMAIN_GUIDELINES_HEADER}\n{self.domain_prompt}"


def load_domain_guideline(domain_id: str, service_key: str) -> str | None:
    """Load the per-domain, per-use-case guideline file, if one exists.

    These live at ``prompts/domains/<domain_id>/<service_key>.md`` and hold
    free-form domain-specific guidance for that service. Returns ``None``
    if no such file has been created for this domain/service combination.
    """
    path = _DOMAINS_DIR / domain_id / f"{service_key}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def render_default_domain_prompt(domain_config: DomainConfig) -> str:
    """Render a generic domain prompt from a ``DomainConfig``."""
    lines: list[str] = [f"Domain: {domain_config.display_name}"]

    if domain_config.datasets:
        lines.append("\nDatasets:")
        lines += [f"- {d.name}: {d.description}" for d in domain_config.datasets]

    if domain_config.metrics:
        lines.append("\nMetrics:")
        for m in domain_config.metrics:
            unit = f" ({m.unit})" if m.unit else ""
            lines.append(f"- {m.name}{unit}: {m.description}")

    if domain_config.dimensions:
        lines.append("\nDimensions:")
        for dim in domain_config.dimensions:
            examples = f" e.g. {', '.join(dim.example_values)}" if dim.example_values else ""
            lines.append(f"- {dim.name}: {dim.description}{examples}")

    if domain_config.business_rules:
        lines.append("\nBusiness rules:")
        lines += [f"- {rule}" for rule in domain_config.business_rules]

    if domain_config.terminology:
        lines.append("\nTerminology:")
        lines += [f"- {term}: {definition}" for term, definition in domain_config.terminology.items()]

    return "\n".join(lines)


def get_prompt_bundle(service_module: ModuleType, service_key: str, domain_config: DomainConfig) -> PromptBundle:
    """Build the ``PromptBundle`` for a service.

    ``service_module`` must define a ``SYSTEM_PROMPT`` constant, which is
    used verbatim and never contains domain knowledge. The domain prompt is
    assembled for ``domain_config`` (selected via the ``--domain`` CLI/UI
    argument) and ``service_key`` from, in order: the generic catalogue
    rendered from ``domain_config``, any inline
    ``domain_prompt_overrides[service_key]``, and any
    ``prompts/domains/<domain_id>/<service_key>.md`` guideline file.
    """
    parts = [render_default_domain_prompt(domain_config)]

    override = domain_config.domain_prompt_overrides.get(service_key)
    if override:
        parts.append(override)

    guideline = load_domain_guideline(domain_config.domain_id, service_key)
    if guideline:
        parts.append(guideline)

    domain_prompt = "\n\n".join(parts)
    return PromptBundle(system_prompt=service_module.SYSTEM_PROMPT, domain_prompt=domain_prompt)
