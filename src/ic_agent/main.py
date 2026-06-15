"""CLI entrypoint.

Usage:
    uv run ic-agent --domain example --query "Why did revenue decline in East China during Q1?"
"""

import argparse
import logging

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.settings import get_settings
from ic_agent.graph.build_graph import build_app
from ic_agent.models.state import AgentState
from ic_agent.utils.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the IC agent analytics pipeline.")
    parser.add_argument("--domain", default="china_sales", help="Domain config id (config/domains/<id>.yaml)")
    parser.add_argument("--query", required=True, help="Business question to investigate")
    parser.add_argument("--log-level", default=None, help="Override the configured log level")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    settings = get_settings()
    configure_logging(level=args.log_level or settings.log_level)

    domain_config = load_domain_config(args.domain, base_dir=settings.domain_config_dir)
    app = build_app(domain_config, settings)

    initial_state: AgentState = {
        "query": args.query,
        "domain_config": domain_config,
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

    logger.info("Done. stop_reason=%s confidence=%.2f", final_state.get("stop_reason"), final_answer.confidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
