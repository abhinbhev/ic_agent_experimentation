"""Streamlit UI for the unified domain super-agent.

Two-column layout: the left column streams each node's output as before,
the right column shows a live "Question Graph" — the entire tree of
super-probes, domain assignments, sub-agent rounds, sub-probes, and
retrieval calls — that updates as the investigation runs.

Run with::

    uv run streamlit run ui/unified_app.py
"""

from __future__ import annotations

import sys
import threading
import traceback
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Make the local components package importable when launching via `streamlit run`
_UI_DIR = Path(__file__).resolve().parent
if str(_UI_DIR) not in sys.path:
    sys.path.insert(0, str(_UI_DIR))

from components.question_graph import render_question_graph  # noqa: E402

from ic_agent.config.domain_loader import load_domain_config  # noqa: E402
from ic_agent.config.settings import get_settings  # noqa: E402
from ic_agent.utils.logging_setup import configure_logging  # noqa: E402
from unified_domain.graph.build_graph import build_unified_app  # noqa: E402
from unified_domain.observability import EventBus, build_tree  # noqa: E402

st.set_page_config(page_title="IC Agent — Unified Domain", layout="wide")

settings = get_settings()
configure_logging(level=settings.log_level)

# --------------------------------------------------------------------- #
# Sidebar: domain list, query, run, panel mode
# --------------------------------------------------------------------- #
domain_dir = Path(settings.domain_config_dir)
available_domains = []
for yaml_path in sorted(domain_dir.glob("*.yaml")):
    if yaml_path.stem == "example":
        continue
    available_domains.append(load_domain_config(yaml_path.stem, base_dir=domain_dir))

with st.sidebar:
    st.markdown("### IC Agent — Unified")
    st.caption(
        f"model: `{settings.openai_model}` · retrieval: `{settings.retrieval_mode}` · "
        f"embeddings: `{settings.embedding_backend}`"
    )
    st.markdown("**Available domains:**")
    for d in available_domains:
        st.write(f"- {d.display_name}")

    query = st.text_area(
        "Business question",
        "How is Brahma performing across brand health and consumption in Brazil?",
        height=120,
    )
    mock_retrieval = st.checkbox(
        "🧪 Mock retrieval",
        value=False,
        help=(
            "If on, the retrieval layer returns canned 'Mock answer to: …' "
            "strings instead of calling the real analysis_template_svc. "
            "Useful for testing planner/decision logic without a backend."
        ),
    )
    run = st.button("Run", type="primary", use_container_width=True)

    st.divider()
    st.markdown("**Live graph panel**")
    panel_mode = st.radio(
        "Panel",
        options=["Split", "Hidden", "Fullscreen"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )


# --------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------- #
def _init_session_state() -> None:
    ss = st.session_state
    ss.setdefault("event_bus", EventBus())
    ss.setdefault("stream_log", [])  # list[tuple[str, dict]]
    ss.setdefault("run_thread", None)
    ss.setdefault("run_error", None)
    ss.setdefault("run_status", "idle")  # idle | running | done | error


_init_session_state()


# --------------------------------------------------------------------- #
# Background runner
# --------------------------------------------------------------------- #
def _run_in_background(
    query_text: str,
    bus: EventBus,
    stream_log: list,
    domains: list,
    domain_knowledge_doc: str,
    run_settings,
) -> None:
    """Execute the super-agent run in a background thread.

    The thread appends ``(node_name, update)`` tuples to ``stream_log``
    for the UI to render, and emits graph events into ``bus``.
    """
    try:
        app = build_unified_app(domains, run_settings, domain_knowledge_doc)
        initial_state = {
            "query": query_text,
            "available_domains": domains,
            "domain_knowledge_doc": domain_knowledge_doc,
            "evidence_ledger": [],
            "rounds_completed": 0,
            "probes_completed_this_round": 0,
            "total_probes_completed": 0,
            "remaining_gaps": [],
            "confidence": 0.0,
            "event_bus": bus,
        }
        for step in app.stream(initial_state, config={"recursion_limit": 100}):
            for node_name, update in step.items():
                stream_log.append((node_name, update))
        st.session_state.run_status = "done"
    except Exception as exc:  # pragma: no cover — UI safety net
        st.session_state.run_error = f"{exc!s}\n\n{traceback.format_exc()}"
        st.session_state.run_status = "error"


# --------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------- #
_DATA_SEPARATOR = "\n\nData:\n"
_TRUNCATE_CHARS = 300


def _render_result(result: str) -> None:
    if _DATA_SEPARATOR in result:
        summary, data_block = result.split(_DATA_SEPARATOR, 1)
        if summary.strip():
            st.write(summary.strip())
        with st.expander("Raw data", expanded=False):
            st.code(data_block, language="json")
    else:
        truncated = result if len(result) <= _TRUNCATE_CHARS else result[:_TRUNCATE_CHARS] + "…"
        st.write(truncated)


def render_step(node_name: str, update: dict) -> None:  # noqa: C901
    if node_name == "similar_plan":
        with st.expander("🔎 Similar Plan Service — matched precedents", expanded=False):
            patterns = update.get("similar_patterns", [])
            if not patterns:
                st.write("No matching patterns found.")
            for p in patterns:
                st.markdown(f"**{p.pattern_id}** (confidence {p.confidence:.2f}) — {p.reason}")
                st.write("Probe strategy:", p.probe_strategy)

    elif node_name == "planner_consultant":
        plan = update["consultant_plan"]
        with st.expander(f"🧭 Planner Consultant — {plan.objective}", expanded=True):
            st.markdown(f"**Success criteria:** {plan.success_criteria}")
            st.markdown("**Hypotheses:**")
            for h in plan.hypotheses:
                st.write(f"- [{h.status}] {h.id}: {h.description}")
            st.markdown("**Probe candidates:**")
            for pc in plan.probe_candidates:
                st.write(f"- ({pc.expected_value}) {pc.id}: {pc.goal} — {pc.reason}")
            if plan.open_questions:
                st.markdown("**Open questions:**")
                for q in plan.open_questions:
                    st.write(f"- {q}")

    elif node_name == "domain_router":
        assignments = update.get("domain_assignments", [])
        total = sum(len(a.probes) for a in assignments)
        with st.expander(f"🗂️ Domain Router — {total} assignment(s)", expanded=True):
            if not assignments:
                st.write("No domain assignments produced.")
            for a in assignments:
                st.markdown(f"**Domain: {a.domain_display_name}**")
                for dp in a.probes:
                    st.write(f"- Probe {dp.probe_candidate_id}: {dp.scoped_question}")
                    st.caption(f"↳ {dp.reason}")

    elif node_name == "domain_execution":
        count = update.get("probes_completed_this_round", 0)
        if count == 0:
            return
        ledger = update.get("evidence_ledger", [])
        new_entries = ledger[-count:]
        with st.expander(f"📡 Domain Execution — {count} probe(s) executed", expanded=True):
            for e in new_entries:
                st.markdown(f"**[{e.source_domain_id}] Q:** {e.question}")
                _render_result(e.result)
                st.divider()

    elif node_name == "decision_consultant":
        out = update["decision_consultant_output"]
        with st.expander(f"⚖️ Decision Consultant — confidence {out.confidence:.2f}", expanded=True):
            if out.remaining_gaps:
                st.markdown("**Remaining gaps:**")
                for g in out.remaining_gaps:
                    st.write(f"- [{g.category}] {g.description}")
            if out.new_hypotheses:
                st.markdown("**New hypotheses:**")
                for h in out.new_hypotheses:
                    st.write(f"- {h.id}: {h.description}")

    elif node_name == "decision_engine":
        out = update["decision_engine_output"]
        with st.expander(
            f"🛑 Decision Engine — {'continue' if out.continue_ else 'stop'} "
            f"(value={out.expected_incremental_value:.2f}, reason={out.stop_reason})",
            expanded=True,
        ):
            st.write(out.reason)
            if out.recommended_next_gap:
                st.write(f"Recommended next gap: {out.recommended_next_gap}")
            st.json(out.value_breakdown.model_dump())

    elif node_name == "synthesis":
        st.markdown("## Final Answer")
        st.markdown(update["final_answer"].markdown)
        st.caption(f"Confidence: {update['final_answer'].confidence:.2f}")


# --------------------------------------------------------------------- #
# Trigger a new run
# --------------------------------------------------------------------- #
if run:
    # Reset session state for the new run
    new_bus = EventBus()
    st.session_state.event_bus = new_bus
    st.session_state.stream_log = []
    st.session_state.run_error = None
    st.session_state.run_status = "running"

    knowledge_doc_path = Path(settings.usecase_docs_dir) / "unified_domain" / "knowledge_doc.md"
    domain_knowledge_doc = (
        knowledge_doc_path.read_text(encoding="utf-8") if knowledge_doc_path.exists() else ""
    )

    # If the user ticked the "Mock retrieval" checkbox, override
    # ``retrieval_mode`` on a per-run settings copy so the cached
    # singleton is left untouched.
    run_settings = (
        settings.model_copy(update={"retrieval_mode": "mock"}) if mock_retrieval else settings
    )

    thread = threading.Thread(
        target=_run_in_background,
        args=(
            query,
            new_bus,
            st.session_state.stream_log,
            available_domains,
            domain_knowledge_doc,
            run_settings,
        ),
        daemon=True,
        name="unified-agent-run",
    )
    st.session_state.run_thread = thread
    thread.start()


# --------------------------------------------------------------------- #
# Auto-refresh while running
# --------------------------------------------------------------------- #
if st.session_state.run_status == "running":
    st_autorefresh(interval=1000, key="unified-graph-poll")


# --------------------------------------------------------------------- #
# Layout: left (stream) | right (graph)
# --------------------------------------------------------------------- #
if panel_mode == "Hidden":
    col_main = st.container()
    col_graph = None
elif panel_mode == "Fullscreen":
    col_main = None
    col_graph = st.container()
else:
    col_main, col_graph = st.columns([3, 2], gap="medium")


# --- Left: stream ---
if col_main is not None:
    with col_main:
        st.title("IC Agent — Unified Domain")
        if st.session_state.run_status == "idle":
            st.info("Enter a question in the sidebar and click **Run** to start an investigation.")
        elif st.session_state.run_status == "running":
            st.caption("Running…  the graph on the right updates in real time.")
        elif st.session_state.run_status == "done":
            st.success("Investigation complete.")
        elif st.session_state.run_status == "error":
            st.error("Run failed.")
            with st.expander("Traceback", expanded=False):
                st.code(st.session_state.run_error or "(no detail)")

        # Render all logged steps so far
        for node_name, update in st.session_state.stream_log:
            render_step(node_name, update)


# --- Right: live graph ---
if col_graph is not None:
    with col_graph:
        tree = build_tree(st.session_state.event_bus.snapshot())
        render_question_graph(tree, height=820)
