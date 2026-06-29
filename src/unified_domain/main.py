"""CLI entrypoint for the unified (super-agent) pipeline.

Usage:
    uv run ic-agent-unified --query "How is brand health evolving across domains?"
"""

import argparse
import logging
from pathlib import Path

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.settings import get_settings
from ic_agent.utils.logging_setup import configure_logging
from unified_domain.graph.build_graph import build_unified_app
from unified_domain.models.state import UnifiedAgentState

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the unified (super-agent) analytics pipeline."
    )
    parser.add_argument("--query", required=True, help="Business question to investigate")
    parser.add_argument("--log-level", default=None, help="Override the configured log level")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    settings = get_settings()
    configure_logging(level=args.log_level or settings.log_level)

    # Load all available domain configs
    domain_dir = Path(settings.domain_config_dir)
    available_domains = []
    for yaml_path in sorted(domain_dir.glob("*.yaml")):
        if yaml_path.stem == "example":
            continue
        available_domains.append(load_domain_config(yaml_path.stem, base_dir=domain_dir))

    # Load consolidated knowledge doc
    knowledge_doc_path = Path(settings.usecase_docs_dir) / "unified_domain" / "knowledge_doc.md"
    domain_knowledge_doc = (
        knowledge_doc_path.read_text(encoding="utf-8") if knowledge_doc_path.exists() else ""
    )

    app = build_unified_app(available_domains, settings, domain_knowledge_doc)

    initial_state: UnifiedAgentState = {
        "query": args.query,
        "available_domains": available_domains,
        "domain_knowledge_doc": domain_knowledge_doc,
        "evidence_ledger": [],
        "rounds_completed": 0,
        "probes_completed_this_round": 0,
        "total_probes_completed": 0,
        "remaining_gaps": [],
        "confidence": 0.0,
    }

    final_state = app.invoke(initial_state, config={"recursion_limit": 100})

    final_answer = final_state["final_answer"]
    print(final_answer.markdown)

    logger.info(
        "Done. stop_reason=%s confidence=%.2f",
        final_state.get("stop_reason"),
        final_answer.confidence,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
