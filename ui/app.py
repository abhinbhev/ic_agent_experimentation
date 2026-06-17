"""Minimal Streamlit UI for exercising the IC agent graph end to end.

Run with:
    uv run streamlit run ui/app.py

Lets you pick a domain + type a business question, then streams each
graph node's output (Similar Plan, Planner Consultant, Planner,
Retrieval, Decision Consultant, Decision Engine) as the agent runs,
finishing with the synthesized markdown answer.
"""

from pathlib import Path

import streamlit as st

from ic_agent.config.domain_loader import load_domain_config
from ic_agent.config.settings import get_settings
from ic_agent.graph.build_graph import build_app
from ic_agent.models.state import AgentState
from ic_agent.utils.logging_setup import configure_logging

st.set_page_config(page_title="IC Agent", layout="wide")

settings = get_settings()
configure_logging(level=settings.log_level)

st.title("IC Agent Experimentation")
st.caption(
    f"model: {settings.openai_model} · retrieval mode: {settings.retrieval_mode} · "
    f"embedding backend: {settings.embedding_backend}"
)

domain_ids = sorted(p.stem for p in Path(settings.domain_config_dir).glob("*.yaml"))

with st.sidebar:
    domain_id = st.selectbox("Domain", domain_ids, index=0)
    query = st.text_area("Business question", "Why did revenue decline in East China during Q1?", height=120)
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


def render_step(node_name: str, update: dict) -> None:
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

    elif node_name == "planner":
        with st.expander("🗂️ Planner — selected probes", expanded=True):
            for tc in update.get("tool_calls", []):
                st.markdown(f"**`{tc.usecase}`** → {tc.question}")
                if tc.reason:
                    st.caption(f"↳ {tc.reason}")

    elif node_name == "execution":
        ledger = update.get("evidence_ledger", [])
        new_entries = ledger[-update.get("probes_completed_this_round", 0) :]
        with st.expander(f"📡 Retrieval — {len(new_entries)} probe(s) executed", expanded=True):
            for e in new_entries:
                st.markdown(f"**Q:** {e.question}")
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
    domain_config = load_domain_config(domain_id, base_dir=settings.domain_config_dir)
    app = build_app(domain_config, settings)

    initial_state: AgentState = {
        "query": query,
        "domain_config": domain_config,
        "evidence_ledger": [],
        "rounds_completed": 0,
        "probes_completed_this_round": 0,
        "total_probes_completed": 0,
        "remaining_gaps": [],
        "confidence": 0.0,
    }

    with st.status("Running agent...", expanded=True) as status:
        for step in app.stream(initial_state, config={"recursion_limit": 100}):
            for node_name, update in step.items():
                render_step(node_name, update)
        status.update(label="Done", state="complete")
