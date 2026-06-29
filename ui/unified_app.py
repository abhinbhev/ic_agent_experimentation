"""Streamlit UI for the unified domain super-agent.

Run with:
    uv run streamlit run ui/unified_app.py
"""

from pathlib import Path

import streamlit as st

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.settings import get_settings
from ic_agent.utils.logging_setup import configure_logging
from unified_domain.graph.build_graph import build_unified_app

st.set_page_config(page_title="IC Agent — Unified Domain", layout="wide")

settings = get_settings()
configure_logging(level=settings.log_level)

st.title("IC Agent — Unified Domain")
st.caption(
    f"model: {settings.openai_model} · retrieval mode: {settings.retrieval_mode} · "
    f"embedding backend: {settings.embedding_backend}"
)

# Load all non-example domains at module level so they show in the sidebar
# before a run is triggered.
domain_dir = Path(settings.domain_config_dir)
available_domains = []
for yaml_path in sorted(domain_dir.glob("*.yaml")):
    if yaml_path.stem == "example":
        continue
    available_domains.append(load_domain_config(yaml_path.stem, base_dir=domain_dir))

with st.sidebar:
    st.markdown("**Available domains:**")
    for d in available_domains:
        st.write(f"- {d.display_name}")

    query = st.text_area(
        "Business question",
        "How is Brahma performing across brand health and consumption in Brazil?",
        height=120,
    )
    run = st.button("Run", type="primary", use_container_width=True)


_DATA_SEPARATOR = "\n\nData:\n"
_TRUNCATE_CHARS = 300


def _render_result(result: str) -> None:
    """Render a retrieval result: summary as text, raw data in a collapsed block."""
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


if run:
    knowledge_doc_path = Path(settings.usecase_docs_dir) / "unified_domain" / "knowledge_doc.md"
    domain_knowledge_doc = (
        knowledge_doc_path.read_text(encoding="utf-8") if knowledge_doc_path.exists() else ""
    )

    app = build_unified_app(available_domains, settings, domain_knowledge_doc)

    initial_state = {
        "query": query,
        "available_domains": available_domains,
        "domain_knowledge_doc": domain_knowledge_doc,
        "evidence_ledger": [],
        "rounds_completed": 0,
        "probes_completed_this_round": 0,
        "total_probes_completed": 0,
        "remaining_gaps": [],
        "confidence": 0.0,
    }

    with st.status("Running unified agent...", expanded=True) as status:
        for step in app.stream(initial_state, config={"recursion_limit": 100}):
            for node_name, update in step.items():
                render_step(node_name, update)
        status.update(label="Done", state="complete")
