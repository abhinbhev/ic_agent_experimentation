# IC Agent — Feature Backlog

Rough priority order. None of these are in scope yet.

---

## 1. Parallelised API calls

**What:** Run all probes in a round concurrently using `asyncio.gather` instead of sequentially.

**Why:** Retrieval is the dominant latency bottleneck. 5 probes × ~2s each = 10s sequential vs ~2s parallel.

**How:** Replace `HttpRetrievalClient` with an `AsyncHttpRetrievalClient` (`httpx.AsyncClient`), make `execution` node async, gather all `ToolCall`s in one `asyncio.gather`.

---

## 2. Interim round summaries

**What:** After each round's Decision Consultant runs, show the user a 3–5 line progress update — what was found, what's still open, confidence so far.

**Why:** Currently the UI is silent until synthesis. Users have no sense of progress mid-run.

**How:** Add a lightweight node between Decision Consultant and Decision Engine that makes a short LLM call (or deterministically templates from `confidence`, `remaining_gaps`, `new_hypotheses`). Stream it to the UI like any other node.

---

## 3. Suggested next steps

**What:** At the end of a completed run, surface 3–5 suggested *angles of analysis* the user could take next — not pre-formed questions, but directions ("look at a competitor", "drill into a demographic", "track this over a longer time horizon").

**Why:** Users often don't know what to ask after seeing results. Surfacing follow-on angles lowers the barrier to continued investigation and makes the agent feel like a thinking partner rather than a query executor.

**How:** Add a post-synthesis LLM call (or fold into Synthesizer output schema) that reads the final answer + remaining unknowns and produces a short list of `{angle, rationale}` pairs. Angles should be phrased as directions, not questions — the user decides the exact framing. Render as a "Where to look next" section in the UI, each item clickable to pre-fill the query box.

---

## 4. Artefact / file system

**What:** Write full evidence results to temp files; keep only metadata (probe_id, question, relevance_score, file path) in LangGraph state.

**Why:** Large SQL dumps in state get expensive as ledger grows. State should be lightweight; full data loaded on demand by nodes that need it (Decision Consultant, Synthesizer).

**How:** On evidence write, dump `result` to `tmp/<run_id>/<probe_id>.txt`. State carries a `result_path` pointer. Nodes that need full text load it at call time.

---

## 5. Conversational / cross-run memory

**What:** Persist the final answer, confirmed hypotheses, and key findings from a completed run so a follow-up question seeds from prior findings rather than starting cold.

**Why:** "Now look at Q2" or "do the same for Mexico" should inherit Q1 Brazil context.

**How:** After synthesis, write a structured summary (question, domain, key findings, confidence) to a persistent store (could reuse `corpus/similar_plans.yaml` format or a separate `memory/` YAML). Planner Consultant receives prior-run summaries alongside the similar-plan results for the new question.

---

## 6. Python sandbox tool

**What:** A tool the agent can call to execute arbitrary Python code — statistical models, data transformations, correlation analysis, anything the retrieval API can't do.

**Why:** Some analytical questions can't be answered by fetching data alone. The agent needs to be able to compute on what it retrieves — e.g. fit a trend line, calculate index scores, run a regression across SQL rows, or produce a derived metric not in the schema.

**How:** Add a `python_sandbox` tool alongside `retrieval_query` in the Planner's tool set. Execution node routes `ToolCall`s with `tool_name="python_sandbox"` to a sandboxed subprocess (or a FastMCP-hosted code execution server). The sandbox receives the code string + any prior SQL data it needs as JSON input, and returns stdout + any serialised output (dataframes, scalars). Results go into the evidence ledger like any retrieval result. Security boundary is critical — subprocess isolation or a containerised execution environment, never `exec` in-process.

---

## 7. Chart generation

**What:** A chart-generation node (or tool) that reads SQL rows from the `Data:` section, calls an LLM to pick chart type and axes, and renders a Plotly/Vega-Lite chart in the UI.

**Why:** Tabular SQL output is hard to scan. A bar or line chart of brand power over time communicates faster.

**How:** After execution, pass each probe's `sql_result` rows to an LLM with a structured output schema (`{chart_type, x_field, y_field, color_field, title}`). Render in Streamlit with `st.plotly_chart`. MCP tool wrapper makes it reusable outside this agent. Needs the most design work of all items here.
