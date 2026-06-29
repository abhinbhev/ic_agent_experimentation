# IC Agent Experimentation

A LangGraph-based agentic analytics framework. Given a business question and a domain, it runs an iterative investigation loop — forming hypotheses, selecting KPIs, executing data-fetch queries against a retrieval API, evaluating evidence, and deciding whether another round is worth running — until it produces a business-facing markdown report.

The project ships **two agents**:

- **Single-domain agent** (`ic-agent`) — investigates one domain at a time. See `docs/flow_diagram.html` for the interactive diagram (with a Brahma in Brazil Q1 2026 worked example).
- **Unified super-agent** (`ic-agent-unified`) — orchestrates multiple single-domain agents in parallel to answer cross-domain questions. See `docs/unified_flow_diagram.html` for the interactive diagram.

---

## Quick start

```bash
uv sync
cp .env.example .env
# Fill in your OPENAI_API_KEY and retrieval API settings in .env
```

**CLI:**
```bash
# Single-domain agent
uv run ic-agent --domain gai_copilot_marketing_brand_guidance_ghq \
  --query "How did Brahma in Brazil perform in Q1 2026?"

# Unified super-agent (auto-discovers all domains)
uv run ic-agent-unified --query "How did Brahma in Brazil perform in Q1 2026 across perception and consumption?"
```

**Streamlit UI:**
```bash
uv run streamlit run ui/app.py            # single-domain
uv run streamlit run ui/unified_app.py    # unified super-agent
```

**Tests** (no API key required):
```bash
uv run pytest -v
```

---

## How it works

The agent runs as a LangGraph state machine. Each "round" executes these nodes in sequence:

```
START → Similar Plan → Planner Consultant → Planner → Execution
      → Decision Consultant → Decision Engine
      ──(continue)──→ Planner Consultant  (next round)
      ──(stop)──────→ Synthesizer → END
```

### Node responsibilities

| Node | Type | What it does |
|------|------|-------------|
| **Similar Plan** | Pure logic | Hybrid search (BM25 + embeddings) over `corpus/similar_plans.yaml` to seed the first round with investigation archetypes |
| **Planner Consultant** | LLM · domain-agnostic | Turns the question + prior evidence into hypotheses and directional probe goals — no KPI names, no tool references |
| **Planner** | LLM · domain-grounded | Selects KPIs from `question_format.md`, writes data-fetch questions the retrieval API can parse, deduplicates against prior rounds, routes to usecases |
| **Execution** | Pure logic | Calls the retrieval API for each question; stores narrative summary + raw SQL rows in the evidence ledger |
| **Decision Consultant** | LLM · domain-agnostic | Evaluates the full evidence ledger; categorises remaining gaps (`closed/partial/open/conflicting`); estimates confidence |
| **Decision Engine** | Deterministic + small LLM | Computes Incremental Value Framework score; checks stop conditions in order; picks the recommended next gap if continuing |
| **Synthesizer** | LLM | Reads the full ledger and writes a clean, business-facing markdown report — no system metadata, every number traced to the data. Receives the same domain context as the Planner (`usecase_docs`, `schema_doc`) so it can correctly interpret KPI names and scales. |

### Separation of concerns

The two "Consultant" components are **KPI-agnostic** — they reason in plain business language about hypotheses and gaps, never naming specific metrics or data sources. The **Planner** and **Decision Engine** are domain-grounded and handle the translation from directional intent to concrete KPI/dimension terms.

This separation means:
- You can swap the retrieval service or change KPI nomenclature without touching the planning layer.
- The Planner Consultant's output is portable across domains and data platforms.

### Planner question rules

The Planner enforces two key constraints when forming retrieval questions:

**Retrieval orientation** — questions are data-fetch requests, not analytical tasks:
- ✅ `"What is the power of all brands in Brazil in Q1 2026?"`
- ❌ `"Compare Brahma vs competitors on brand power"`

**Coverage subsumption** — before writing each new question the Planner checks what earlier probes in the same batch already cover. If an earlier question returns the needed data, the new probe reuses that coverage instead of generating a duplicate. Where possible, one question is designed to be broad enough to serve multiple probes (e.g. a multi-period fetch for Q4 2025 + Q1 2026 covers both a trend probe and a current-period probe). After all questions are formed, a consolidation pass marks any remaining duplicates with `keep=false`; the service drops these before execution.

### Evidence format

Each evidence ledger entry's `result` field contains:
```
<Narrative summary from the retrieval service>

Data:
[{...raw SQL result rows as JSON...}]
```

The `Data:` section is the ground-truth numbers. Both the Decision Consultant and Synthesizer prompts instruct the LLM to read it directly rather than relying on the summary narrative.

### Stop conditions

The Decision Engine checks these in order (first match wins):
1. `max_rounds_reached`
2. `max_total_probes_reached`
3. `all_major_gaps_closed`
4. `no_progress_this_round` — stall detected: the Planner produced zero questions, or every probe executed this round was marked irrelevant by the Decision Consultant
5. `incremental_value_below_threshold`
6. `continue`

---

## Unified super-agent (cross-domain)

The **super-agent** (`ic-agent-unified`) mirrors the single-agent's 7-node loop, but replaces the retrieval API call with **parallel single-domain agent invocations**. It is purely additive — no existing code is modified.

```
START → Unified Similar Plan → Unified Planner Consultant → Domain Router
      → Domain Agent Executor (parallel sub-agent runs via asyncio.gather)
      → Unified Decision Consultant → Unified Decision Engine
      ──(continue)──→ Unified Planner Consultant
      ──(stop)──────→ Unified Synthesizer → END
```

### Two key substitutions vs. the single-agent

| Single-agent node | Super-agent equivalent | Difference |
|---|---|---|
| **Planner** (KPI selection) | **Domain Router** | Assigns each probe to one or more sub-domains and writes a self-contained scoped question. Sees only domain display names + dataset descriptions — no KPI knowledge. |
| **Execution** (HTTP retrieval) | **Domain Agent Executor** | For each `DomainProbe`, builds a fresh single-agent graph and `await app.ainvoke(...)`. All sub-agents run concurrently via `asyncio.gather`. Each sub-agent's `final_answer.markdown` becomes one cross-domain evidence entry. |

### Zero-shot prompts

Every super-agent LLM component (Planner Consultant, Domain Router, Decision Consultant, Decision Engine, Synthesizer) uses a **zero-shot system prompt**: no domain names, no KPI references, no dataset specifics in the static prompt. Domain context comes only via the human message payload:
- `available_domains` — list of registered sub-domains with dataset descriptions
- `domain_knowledge_doc` — `docs/metadata/unified_domain/knowledge_doc.md`, a KPI-free overview of every sub-domain and how they relate

The Unified Planner Consultant is instructed to reason about **domain-knowledge-based probes** (what kinds of business questions each sub-domain can answer) — *not* about specific KPIs. KPI selection stays inside each sub-agent's own Planner.

### Parallel execution

The Domain Agent Executor dispatches all `DomainAssignment`s concurrently. Sub-agents are fully independent — no shared state, no shared cache. Failures in one sub-agent are caught and logged; the super-agent continues with the remaining successful entries.

### Budget

```yaml
# config/unified_probe_budget.yaml
probe_budget:
  max_rounds: 2
  max_probes_per_round: 3
  max_total_probes: 5
```

A super-agent "probe" is one sub-agent invocation. Each sub-agent has its own internal budget (3 rounds × 5 probes × 8 total), so worst case is ~40 retrieval API calls across all sub-agents in one super-agent run.

### Evidence

Each `UnifiedEvidenceLedgerEntry` carries:
- `result` — the sub-agent's synthesized markdown report (for Decision Consultant + Synthesizer)
- `sub_evidence` — the sub-agent's full internal evidence ledger (for traceability / debugging)
- `source_domain_id` — which sub-domain produced this entry

### Files added (super-agent only — single-agent untouched)

```
src/unified_domain/                            # all super-agent code
├── models/                                    # state, domain_router, evidence
├── prompts/                                   # zero-shot SYSTEM_PROMPT constants
├── services/                                  # one service per node
├── graph/                                     # build_graph, nodes, edges
└── main.py                                    # ic-agent-unified CLI

config/unified_probe_budget.yaml               # super-agent budget
docs/metadata/unified_domain/knowledge_doc.md  # consolidated KPI-free domain doc
ui/unified_app.py                              # Streamlit UI for super-agent
tests/unified/                                 # 18 unit + integration tests
```

See `docs/unified_flow_diagram.html` for the interactive diagram.

---

## Configuration

### Probe budget (`config/probe_budget.yaml`)

```yaml
probe_budget:
  max_rounds: 3
  max_probes_per_round: 5
  max_total_probes: 8

score_fusion:
  bm25_weight: 0.5
  embedding_weight: 0.5
  fusion_method: weighted_sum

incremental_value_weights:
  unresolved_gaps: 0.40
  low_confidence: 0.30
  new_hypotheses: 0.20
  irrelevance: 0.05
  budget_headroom: 0.05
  stop_threshold: 0.30
```

### Domain config (`config/domains/<domain_id>.yaml`)

```yaml
domain_id: my_domain
display_name: "My Domain"
primary_usecase: my_usecase   # key knowledge_doc.md is loaded under (default: brand_guidance)
datasets:
  - name: Brand Guidance
    description: "Survey-based brand health data."
metrics: []
dimensions: []
business_rules: []
terminology: {}
domain_prompt_overrides: {}   # optional per-service prompt additions
```

### Environment variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI key (or omit if using LiteLLM proxy) |
| `IC_AGENT_OPENAI_MODEL` | `gpt-5.4` | Chat model |
| `AZURE_OPENAI_ENDPOINT_LITELLM` | — | LiteLLM proxy URL (overrides direct OpenAI) |
| `AZURE_OPENAI_API_KEY_LITELLM` | — | LiteLLM proxy key |
| `IC_AGENT_RETRIEVAL_MODE` | `http` | `http` or `mock` |
| `IC_AGENT_RETRIEVAL_BASE_URL` | `http://localhost:7777` | Retrieval API base URL |
| `IC_AGENT_RETRIEVAL_USER_ID` | `agentic_experiment` | `user_id` for retrieval API |
| `INTERNAL_API_KEY` | — | `X-Internal-API-Key` header for retrieval API |
| `IC_AGENT_LOG_LEVEL` | `INFO` | Log level |

See `.env.example` for the full list.

---

## Adding a new domain

1. **Domain config:** Create `config/domains/<domain_id>.yaml`.

2. **Metadata files:** Create `docs/metadata/<domain_id>/` and add:
   - `knowledge_doc.md` — what the primary usecase covers (and doesn't). Loaded under the key set by `primary_usecase` in the domain YAML (defaults to `brand_guidance`).
   - `question_format.md` — the retrieval service's NLP extraction guide: valid KPI names, parameter rules, worked examples. This is the Planner's KPI oracle.
   - `COLUMN_DESCRIPTION.csv` — columns with `table_name`, `column_name`, `column_description`

3. **Similar plan corpus:** Add an entry to `corpus/similar_plans.yaml` with a matching `dataset_family`.

4. The domain appears automatically in the UI dropdown and `--domain` CLI argument.

---

## Adding a new retrieval usecase

1. Add the ID to the `Usecase` literal in `src/ic_agent/models/retrieval.py`.
2. Add the template name to `_USECASE_TEMPLATE_MAP` in `src/ic_agent/services/retrieval_service.py`.
3. Add the ID to `_USECASE_IDS` in `src/ic_agent/config/usecase_docs.py`.
4. Create `docs/metadata/<domain_id>/<usecase_id>.md` as the knowledge doc.

---

## Project structure

```
src/ic_agent/
├── config/        # settings, probe budget, domain loader, usecase doc loaders
├── models/        # pydantic v2 models for every service boundary
├── prompts/       # SYSTEM_PROMPT constants + PromptBundle assembly
│   └── domains/   # optional per-domain per-service guideline .md files
├── services/      # one service class per node
├── graph/         # LangGraph wiring (build_graph, nodes, edges)
└── utils/         # logging, IDs, timing
```

**Key architectural files:**
- `src/ic_agent/prompts/base.py` — how static + dynamic prompt parts are combined
- `src/ic_agent/graph/build_graph.py` — how all services are wired into the graph
- `src/ic_agent/services/planner_service.py` — KPI routing, question formation, deduplication
- `src/ic_agent/services/retrieval_service.py` — retrieval API client and evidence format

---

## Tests

```bash
uv run pytest -v                                          # all tests, no API key needed
uv run pytest -v tests/test_end_to_end_graph.py          # full graph with fake LLMs
OPENAI_API_KEY=sk-... uv run pytest -v tests/test_llm_integration.py   # real API call
```

Unit tests use a `FakeStructuredChatModel` test double and a stub embedding backend — no network calls. The integration test (`test_llm_integration.py`) makes a real OpenAI call and is auto-skipped unless `OPENAI_API_KEY` is set.

---

## Documentation

| File | What's in it |
|------|-------------|
| `docs/archetecture.md` | Original architecture specification |
| `docs/prompt_of_prompts.md` | Prompt design guide and style reference |
| `docs/flow_diagram.html` | Interactive flow diagram (single-domain agent) — open in browser; includes a full worked example using real Brahma/Brazil Q1 2026 data |
| `docs/unified_flow_diagram.html` | Interactive flow diagram for the **unified super-agent**: 7-node loop, Domain Router, parallel sub-agent execution |
| `docs/metadata/unified_domain/knowledge_doc.md` | Consolidated cross-domain knowledge doc fed to the Unified Planner Consultant + Synthesizer at runtime (KPI-free) |
| `CLAUDE.md` | Comprehensive technical reference for AI coding assistants: every architectural decision, known pitfall, and file-level explanation (covers both single-agent and super-agent) |
