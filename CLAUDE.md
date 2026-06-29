# CLAUDE.md — IC Agent Experimentation

Everything a fresh Claude session needs to understand, navigate, and extend this codebase without having to rediscover decisions that were already made.

---

## What this repo is

An **agentic analytics framework** built on LangGraph. Given a business question and a domain, it runs an iterative investigation loop:

1. Seeds the first plan with past similar investigation patterns.
2. Plans hypotheses and probe goals (directional, KPI-agnostic).
3. Translates probe goals into concrete retrieval-ready data-fetch questions, selecting KPIs from the domain's `question_format.md`.
4. Executes questions against a retrieval HTTP API; stores results (narrative summary + raw SQL rows) in an evidence ledger.
5. Evaluates the accumulated evidence; identifies remaining gaps and confidence.
6. Decides deterministically whether another round is worth running.
7. Loops or stops; on stop, synthesises a business-facing markdown report.

Two live domains:
- `gai_copilot_marketing_brand_guidance_ghq` — brand health / perception data (`brand_guidance` usecase)
- `gai_copilot_marketing_category_ghq` — consumer consumption data / POS program (`category` usecase)

**There is also a unified super-agent** (`src/unified_domain/`) that orchestrates multiple single-domain agents in parallel to answer cross-domain questions. It mirrors the same 7-node loop but uses single-agents as its "retrieval" layer. See the "Super-Agent (Unified Domain)" section below.

---

## Directory layout

```
ic_agent_experimentation/
├── CLAUDE.md                          # this file
├── README.md
├── pyproject.toml                     # uv-managed; deps, CLI entry point
├── .env.example                       # copy to .env and fill in secrets
│
├── config/
│   ├── probe_budget.yaml              # single-agent budget limits, score-fusion weights, IVF weights
│   ├── unified_probe_budget.yaml      # super-agent budget (separate, tighter)
│   └── domains/
│       ├── gai_copilot_marketing_brand_guidance_ghq.yaml   # LIVE domain — brand health
│       ├── gai_copilot_marketing_category_ghq.yaml         # LIVE domain — category/POS consumption
│       └── example.yaml               # toy domain for testing
│
├── corpus/
│   └── similar_plans.yaml             # investigation archetype corpus for SimilarPlanService
│
├── docs/
│   ├── archetecture.md                # original architecture spec (primary reference)
│   ├── prompt_of_prompts.md           # prompt design guide (style reference)
│   ├── flow_diagram.html              # interactive HTML flow diagram — single-agent
│   ├── unified_flow_diagram.html      # interactive HTML flow diagram — super-agent (Domain Router + parallel)
│   ├── brand highlights refined.pdf   # real run output PDF (used to populate the worked example)
│   ├── brand_highlights_extracted.md  # OCR text of the above PDF
│   └── metadata/
│       ├── gai_copilot_marketing_brand_guidance_ghq/
│       │   ├── knowledge_doc.md       # brand_guidance usecase knowledge doc (fed to Planner + Synthesizer)
│       │   ├── question_format.md     # retrieval NLP extraction guide (fed to Planner — critical)
│       │   ├── COLUMN_DESCRIPTION.csv # column-level schema fed to Planner + Synthesizer
│       │   └── TABLE_DESCRIPTION.csv  # NOT used (user decision: columns are sufficient)
│       ├── gai_copilot_marketing_category_ghq/
│       │   ├── knowledge_doc.md       # category usecase knowledge doc
│       │   ├── question_format.md     # category NLP extraction guide
│       │   └── COLUMN_DESCRIPTION.csv # placeholder (to be filled in)
│       └── unified_domain/
│           └── knowledge_doc.md       # KPI-free cross-domain doc (fed to super-agent Planner Consultant + Synthesizer)
│
├── src/ic_agent/                       # SINGLE-DOMAIN AGENT — unchanged
│   ├── main.py                        # CLI entry point
│   ├── config/
│   │   ├── settings.py                # all env vars in one place (pydantic-settings)
│   │   ├── probe_budget.py            # ProbeBudgetConfig, ScoreFusionWeights, IncrementalValueWeights
│   │   ├── domain_loader.py           # load_domain_config(domain_id)
│   │   └── usecase_docs.py            # load_usecase_docs / load_schema_doc / load_question_format_doc
│   ├── models/
│   │   ├── state.py                   # AgentState TypedDict (the LangGraph state)
│   │   ├── domain.py                  # DomainConfig, DatasetSpec, MetricSpec, DimensionSpec
│   │   ├── similar_plan.py            # SimilarPlanEntry, MatchedPattern, SimilarPlanQuery/Result
│   │   ├── evidence.py                # EvidenceLedgerEntry
│   │   ├── planner_consultant.py      # Hypothesis, ProbeCandidate, PlannerConsultantInput/Output
│   │   ├── planner.py                 # ToolCall, PlannerInput/Output, ProbeUsecaseAssignment
│   │   ├── retrieval.py               # RetrievalQuery, RetrievalResult, Usecase literal
│   │   ├── decision_consultant.py     # RemainingGap, DecisionConsultantInput/Output
│   │   ├── decision_engine.py         # IncrementalValueBreakdown, DecisionEngineInput/Output
│   │   └── synthesizer.py             # SynthesizerInput, SynthesizerOutput
│   ├── prompts/
│   │   ├── base.py                    # PromptBundle + get_prompt_bundle (critical — read this)
│   │   ├── planner_consultant.py      # SYSTEM_PROMPT for Planner Consultant
│   │   ├── planner.py                 # SYSTEM_PROMPT for Planner (KPI selection + question rules)
│   │   ├── decision_consultant.py     # SYSTEM_PROMPT for Decision Consultant
│   │   ├── decision_engine.py         # SYSTEM_PROMPT for Decision Engine gap recommendation
│   │   ├── synthesizer.py             # SYSTEM_PROMPT for Synthesizer
│   │   └── domains/                   # per-domain per-service guideline .md files (optional)
│   ├── services/
│   │   ├── llm_factory.py             # get_chat_model(settings) — OpenAI or LiteLLM proxy
│   │   ├── embeddings.py              # EmbeddingBackend ABC, OpenAI + Ollama backends
│   │   ├── similar_plan_service.py    # hybrid search: BM25 + embeddings + score fusion
│   │   ├── planner_consultant_service.py
│   │   ├── planner_service.py         # KPI routing + question deduplication (core logic)
│   │   ├── retrieval_service.py       # HTTP client for analysis_template_svc
│   │   ├── decision_consultant_service.py
│   │   ├── decision_engine_service.py # deterministic IVF scoring + LLM gap recommendation
│   │   └── synthesizer_service.py
│   ├── graph/
│   │   ├── build_graph.py             # wires all services into the LangGraph StateGraph
│   │   ├── nodes.py                   # make_*_node factories (state → service → state)
│   │   └── edges.py                   # route_after_decision_engine conditional edge
│   └── utils/
│       ├── logging_setup.py
│       ├── ids.py                     # new_probe_id()
│       ├── timing.py                  # now_iso()
│       └── ssl_setup.py
│
├── src/unified_domain/                 # SUPER-AGENT — orchestrates parallel single-agents
│   ├── main.py                        # ic-agent-unified CLI
│   ├── models/                        # UnifiedAgentState, DomainProbe, DomainAssignment, etc.
│   ├── prompts/                       # zero-shot SYSTEM_PROMPTs (no domain/KPI references)
│   ├── services/                      # planner_consultant, domain_router, domain_agent_executor, etc.
│   └── graph/                         # build_graph, nodes, edges for unified StateGraph
│
├── tests/
│   ├── conftest.py                    # FakeStructuredChatModel, fixtures, stub embeddings
│   ├── test_config.py
│   ├── test_planner_service.py
│   ├── test_similar_plan_service.py
│   ├── test_usecase_docs.py
│   ├── test_end_to_end_graph.py
│   ├── test_llm_integration.py        # skipped without OPENAI_API_KEY
│   └── unified/                       # super-agent tests (18 tests)
│       ├── test_domain_router_service.py
│       ├── test_domain_agent_executor.py
│       ├── test_unified_services.py
│       ├── test_unified_end_to_end.py
│       └── test_unified_integration.py # skipped without OPENAI_API_KEY
│
└── ui/
    ├── app.py                         # single-agent UI (uv run streamlit run ui/app.py)
    └── unified_app.py                 # super-agent UI (uv run streamlit run ui/unified_app.py)
```

---

## The 7-node pipeline

### Node 1 — Similar Plan Service (pure logic)

**Purpose:** Seeds the first planning round with investigation archetypes from `corpus/similar_plans.yaml`.

**How:** Three-stage hybrid retrieval:
1. **Stage 1 — metadata filter:** Keep only corpus entries whose `dataset_family` overlaps with the domain's dataset names. Falls back to the full corpus if no overlap.
2. **Stage 2 — dual scoring:** BM25 (lexical) over `intent + description + probe_sequence` text, plus embedding cosine similarity. Embeddings are cached in `corpus/.cache/embeddings_<hash>.json` keyed by a SHA-256 of the corpus text — if the corpus changes, the cache auto-invalidates.
3. **Stage 3 — score fusion:** Min-max normalise each score array separately, then weighted sum (or RRF). `confidence` on each `MatchedPattern` is the fused score.

**Corpus schema** (`corpus/similar_plans.yaml`):
```yaml
- pattern_id: brand_country_period_performance_bg   # _bg suffix = Brand Guidance domain
  intent: "How is a brand's performance in a country in a given period?"
  dataset_family: [Brand Guidance]
  analysis_type: brand_health
  probe_sequence:
    - "change in equity"
    - "factors affecting equity"
    - "perceptions of the brand"
    - "consumption"
    - "demographic insights"
  description: "..."
  stop_condition: "..."
  failure_modes: [...]
```

The `probe_sequence` list from the top-matching corpus entry is passed to the Planner Consultant as `probe_strategy`. The Planner Consultant is instructed to treat it as a **structured checklist**: walk through each item, include a hypothesis or probe for areas that apply, and note skipped items in `open_questions` rather than silently ignoring them.

**Important:** When running tests, always pass `cache_dir=tmp_path` to `SimilarPlanService` to avoid stale cache dimension mismatches between real (1536-dim) and stub (8-dim) embeddings.

---

### Node 2 — Planner Consultant (LLM, domain-agnostic)

**Purpose:** Turns the business question + prior evidence into an investigation plan.

**Key constraint — KPI-agnostic:** Probe candidate `goal` fields MUST be phrased as directional business intents with **no KPI names, metric names, column names, tool references, or data source references**. Examples:
- ✅ "How did Brahma's overall brand health change in Q1 2026 vs prior periods?"
- ❌ "What is the Power and MDS of Brahma in Q1 2026?"

The Planner Consultant knows nothing about KPIs. Its output feeds the Planner, which does KPI selection.

**Multi-round behaviour:** In round 2+, receives `evidence_ledger`, `remaining_gaps`, and `recommended_next_gap`. Step 2 of its REASONING PROCESS explicitly instructs it to review what's already been asked (from `evidence_ledger`) and NOT propose probes that duplicate or closely restate already-answered questions.

**Output:**
```python
PlannerConsultantOutput(
    objective="...",
    hypotheses=[Hypothesis(id, description, status)],          # status: open/supported/refuted
    probe_candidates=[ProbeCandidate(id, goal, expected_value, reason)],  # expected_value: high/medium/low
    success_criteria="...",
    open_questions=["..."],
)
```

---

### Node 3 — Planner (LLM, domain-grounded + pure logic)

**Purpose:** Translates directional probe goals into concrete, retrieval-ready data-fetch questions. The most behaviourally complex component — understand its constraints well.

**KPI selection:** The Planner reads `question_format.md` (the retrieval service's own NLP extraction guide) as the authoritative source of valid KPI names and question patterns. Common mappings in the prompt:
- equity / brand health → `power`
- equity drivers → `meaningful, difference, salience`
- perceptions / imagery → `bip_market` (separate retrieval type) or `affinity_score, meet_need, unique_score, dynamic_score`
- consumption / usage → `consumption_past_seven_days/four_weeks/three_months`
- awareness → `awareness, total_spontaneous_awareness, top_of_mind`
- consideration / trial → `consideration, trial`

**KPI selectivity rule:** Pick the **minimum** set (1–4 KPIs) that directly covers the probe's intent. Never dump all available KPIs in one question.

**Retrieval orientation rule:** Questions must be data-fetch requests ("What is/are X for Y in Z?"), **not** analytical or comparative tasks. Transform like this:
- "Compare Brahma vs competitors" → "What is the power of **all brands** in Brazil in Q1 2026?"
- "How did it change vs prior period?" → "What is [KPI] for Brahma in Brazil in **Q1 2026 and Q4 2025**?" (one multi-period fetch, not two separate calls)

**Proactive design:** Before running the consolidation pass, the Planner is instructed to design questions to be broad enough upfront to serve multiple probes — e.g. a multi-period fetch that covers a trend probe *and* a current-period probe in one call.

**Coverage subsumption (`keep=false` mechanic):** After all questions are generated across all probes in the batch, a consolidation pass identifies questions whose data is fully returned by another question in the same batch. Those are marked `keep=false`; `planner_service.py` drops them deterministically before execution. Period subsumption rule: a question asking for period T is subsumed by any question in the batch that asks for the same KPIs, the same entity scope, and a period set that includes T.

**Multi-KPI grouping:** The retrieval service can handle multiple KPIs in one call. Group related KPIs (e.g. `meaningful, difference, salience`) into one question. Only split into multiple questions when KPIs belong to genuinely distinct retrieval types (e.g. factual KPIs vs `bip_market` imagery) or different dimension cuts (e.g. overall vs demographic breakdown).

**Deduplication (two-layer, cross-round):**
1. **LLM-level:** `asked_questions` (all questions from prior rounds' evidence ledger) are passed in the JSON payload with explicit instruction not to regenerate them.
2. **Deterministic backstop:** `planner_service.py` skips any generated question whose lowercased form is in `asked_questions`. This is the safety net — the LLM constraint should catch most, but this catches any slippage.

**Output per probe:**
```python
ProbeUsecaseAssignment(
    probe_candidate_id="P1",
    questions=[QuestionItem(text="What is the power of Brahma in Brazil in Q1 2026, Q4 2025, and Q1 2025?", keep=True)],
    usecase="brand_guidance",
    reason="power captures overall equity; 3-period fetch covers current, prior-quarter, and prior-year."
)
```
`questions` is a list of `QuestionItem(text, keep)`. Items with `keep=False` are dropped by the service before execution; the list can be empty if a probe is fully subsumed. Each surviving item becomes one `ToolCall`.

**Tool call ordering and capping:** Tool calls are sorted high → medium → low `expected_value` then capped at `max_probes_per_round` (currently 5).

---

### Node 4 — Execution (pure logic)

**Purpose:** Calls the retrieval API for each `ToolCall`; appends results to `evidence_ledger`.

**Retrieval API contract (critical — this burned us):**
- Endpoint: `POST /api/v1/analysis-template-executor/execute`
- `request_id` **must be a UUID** (not a custom string like `"P-abc123"`)
- `request_id` must appear in **both** the URL query params AND the JSON body simultaneously:
  ```python
  request_id = str(uuid.uuid4())
  requests.post(
      url,
      params={"user_id": user_id, "request_id": request_id},
      json={"usecase": template_usecase, "user_question": question,
            "ner_heads": [], "request_id": request_id},
  )
  ```
- Using a non-UUID format or omitting from one location returns `response: ""`, `sql_result: []`.

**Usecase mapping:** Internal usecase IDs map to template names:
```python
_USECASE_TEMPLATE_MAP = {
    "brand_guidance": "gai_copilot_marketing_brand_guidance_ghq",
    "category": "gai_copilot_marketing_category_ghq",
}
```

**Evidence format:** Each `EvidenceLedgerEntry.result` is:
```
<Narrative summary from response["response"]["Summary"]>

Data:
[{...raw SQL result rows as JSON...}]
```
If `response` is empty but `sql_result` exists and is an empty list, a descriptive "no data returned" message is stored instead. The `Data:` section is what the Decision Consultant and Synthesizer prompts explicitly instruct the LLM to read for actual numbers.

---

### Node 5 — Decision Consultant (LLM, domain-agnostic)

**Purpose:** Evaluates the full accumulated evidence ledger against the original question. Categorises remaining gaps, surfaces new hypotheses, estimates confidence.

**Key note:** Like the Planner Consultant, it is **domain-agnostic** — its `remaining_gaps` describe directions in plain business language, not KPI-grounded questions. The Planner grounds those gaps into KPIs in the next round.

**Gap categories:** `closed`, `partial`, `open`, `conflicting`. The Decision Engine counts `open + partial + conflicting` as unresolved.

**Evidence reading:** The prompt explicitly tells it to read the `Data:` section in each `result` for actual numbers rather than relying on the narrative summary alone.

---

### Node 6 — Decision Engine (deterministic scoring + small LLM call)

**Purpose:** Decides continue/stop. The continue/stop decision is **purely deterministic** (reproducible without a model). A small LLM call is used only to produce `recommended_next_gap + reason`.

**Stop conditions checked in order:**
1. `max_rounds_reached` — `rounds_completed >= max_rounds`
2. `max_total_probes_reached` — `total_probes_completed >= max_total_probes`
3. `all_major_gaps_closed` — no `open/partial/conflicting` gaps remain
4. `no_progress_this_round` — stall detected: Planner produced zero questions, or every probe executed this round was marked irrelevant by the Decision Consultant
5. `incremental_value_below_threshold` — weighted IVF score < `stop_threshold`
6. else: `continue`

**Incremental Value Framework (IVF) scoring:**

All five sub-scores are normalized to `[0, 1]` and point the **same** direction: **HIGH = more value in continuing another round**. The engine stops when the weighted sum falls below `stop_threshold`.

```
unresolved_gaps_score  = unresolved_gaps / total_gaps                       weight: 0.40
low_confidence_score   = 1 - decision_consultant.confidence                 weight: 0.30
new_hypotheses_score   = min(new_hypotheses / 3, 1.0)                       weight: 0.20
irrelevance_score      = 1 - relevant_probes / total_probes_completed       weight: 0.05
budget_headroom_score  = max(0, 1 - total_probes / max_total_probes)        weight: 0.05
stop_threshold         = 0.30
```

Rationale: every sub-score is monotonic in the "continue is valuable" direction so the weighted sum can never become a contradictory signal. `unresolved_gaps` and `low_confidence` carry the most weight (they are the strongest "still work to do" signals); `irrelevance` and `budget_headroom` are weak tiebreakers. `budget_headroom` is not really a value signal — it's already gated by the hard `max_total_probes` stop — so it gets the smallest weight.

All weights and the threshold live in `config/probe_budget.yaml` and are runtime-configurable.

---

### Node 7 — Synthesizer (LLM)

**Purpose:** Produces a clean, business-facing markdown report from the full ledger.

**Domain context:** The Synthesizer receives the same `usecase_docs` (knowledge docs per usecase) and `schema_doc` (column-level schema) as the Planner, so it can correctly interpret KPI names and scales when reading the evidence ledger.

**Writing constraints (enforced by prompt):**
- Never mention probe IDs, probe counts, investigation rounds, system internals, or any metadata about how the answer was produced.
- Every number in Key Findings and Evidence must trace to a `result` in the ledger (read the `Data:` section, not just the narrative).
- Where evidence is insufficient, say so; do not fill gaps with plausible-sounding guesses.

**Required sections (in order):** `## Summary`, `## Key Findings`, `## Evidence`, `## Recommendations`, `## Confidence`, `## Remaining Unknowns`.

---

## Prompt architecture

Every LLM-backed service gets a `PromptBundle` assembled by `get_prompt_bundle()` in `prompts/base.py`:

```
system_prompt  (static, defined in prompts/<service>.py)
              +
DOMAIN GUIDELINES
  1. Generic catalogue from DomainConfig (datasets, metrics, dimensions, rules, terminology)
  2. domain_prompt_overrides[service_key] from the domain YAML (inline text)
  3. prompts/domains/<domain_id>/<service_key>.md file (optional per-domain/per-service guideline)
```

The `DOMAIN GUIDELINES` section is appended under that explicit heading so the model can cleanly separate its behavior spec from the dynamic domain context.

**Planner is unique:** In addition to `DOMAIN GUIDELINES`, the Planner receives `usecase_docs`, `question_format`, `schema_doc`, and `asked_questions` in the **human message** JSON payload — these are per-request, not per-domain prompt content.

**Synthesizer also receives domain context:** Unlike other LLM nodes, the Synthesizer receives `usecase_docs` and `schema_doc` in its human message payload (same content as the Planner) so it can correctly interpret KPI names and scales when writing the report.

---

## Domain metadata files

All per-domain metadata lives under `docs/metadata/<domain_id>/`:

| File | Purpose | Fed to |
|------|---------|--------|
| `knowledge_doc.md` | What the primary usecase can/can't answer. Loaded under the key set by `primary_usecase` in the domain YAML (default: `"brand_guidance"`). | Planner + Synthesizer (as `usecase_docs[primary_usecase]`) |
| `question_format.md` | Retrieval service NLP extraction guide: valid KPI names, parameter rules, examples | Planner (as `question_format`) |
| `COLUMN_DESCRIPTION.csv` | Column-level schema (`table_name`, `column_name`, `column_description`) | Planner + Synthesizer (as `schema_doc`) |
| `TABLE_DESCRIPTION.csv` | Table descriptions — **NOT used** (user decision: column descriptions are sufficient) | — |

**To add a new domain:**
1. Create `config/domains/<domain_id>.yaml` with `DomainConfig` fields. Set `primary_usecase` to the retrieval usecase ID the `knowledge_doc.md` covers (e.g. `category`). Defaults to `brand_guidance` if omitted.
2. Create `docs/metadata/<domain_id>/` and populate the above files.
3. Add an entry to `corpus/similar_plans.yaml` with a matching `dataset_family`.
4. The domain appears automatically in the UI dropdown and CLI `--domain` arg.

---

## Environment variables

All read from `.env` via pydantic-settings (`config/settings.py`). None are read anywhere else.

| Env var | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required for LLM calls unless using LiteLLM proxy) |
| `IC_AGENT_OPENAI_MODEL` | `gpt-5.4` | Chat model for all LLM-backed services |
| `IC_AGENT_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `AZURE_OPENAI_ENDPOINT_LITELLM` | — | LiteLLM proxy base URL (overrides direct OpenAI if set) |
| `AZURE_OPENAI_API_KEY_LITELLM` | — | LiteLLM proxy API key (strips `Bearer ` prefix automatically) |
| `IC_AGENT_EMBEDDING_BACKEND` | `openai` | `openai` or `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `IC_AGENT_LOG_LEVEL` | `INFO` | Log level |
| `IC_AGENT_CORPUS_PATH` | `corpus/similar_plans.yaml` | Path to similar plans corpus |
| `IC_AGENT_DOMAIN_DIR` | `config/domains` | Directory of domain YAML files |
| `IC_AGENT_PROBE_BUDGET_PATH` | `config/probe_budget.yaml` | Probe budget config |
| `IC_AGENT_USECASE_DOCS_DIR` | `docs/metadata` | Root of per-domain metadata |
| `IC_AGENT_RETRIEVAL_MODE` | `http` | `http` (real API) or `mock` (returns `"Mock answer to: " + question`) |
| `IC_AGENT_RETRIEVAL_BASE_URL` | `http://localhost:7777` | analysis_template_svc base URL |
| `IC_AGENT_RETRIEVAL_USER_ID` | `agentic_experiment` | `user_id` passed to retrieval API |
| `INTERNAL_API_KEY` | — | `X-Internal-API-Key` header for retrieval API |

**LiteLLM proxy:** If `AZURE_OPENAI_ENDPOINT_LITELLM` is set, `get_chat_model()` uses `ChatOpenAI(base_url=<litellm_base_url>, api_key=<litellm_api_key>)` — same interface, same code, just pointed at the proxy instead of OpenAI directly. The `litellm_base_url` property appends `/v1` to the endpoint automatically.

**Ollama fallback:** If `IC_AGENT_EMBEDDING_BACKEND=ollama` but Ollama is unreachable, `get_embedding_backend()` logs a warning and falls back to OpenAI embeddings silently.

---

## Probe budget config (`config/probe_budget.yaml`)

```yaml
probe_budget:
  max_rounds: 3            # max investigation rounds before forced stop
  max_probes_per_round: 5  # cap on tool calls per round (Planner enforces this)
  max_total_probes: 8      # global cap (Decision Engine enforces this)

score_fusion:
  bm25_weight: 0.5
  embedding_weight: 0.5
  fusion_method: weighted_sum   # or rrf
  rrf_k: 60

incremental_value_weights:
  unresolved_gaps: 0.40
  low_confidence: 0.30
  new_hypotheses: 0.20
  irrelevance: 0.05
  budget_headroom: 0.05
  stop_threshold: 0.30
```

---

## Test strategy

All 38 unit tests run without `OPENAI_API_KEY` using:
- `FakeStructuredChatModel` in `tests/conftest.py` — accepts a queue of pydantic instances to return from `.with_structured_output(...).invoke(...)`.
- Stub `EmbeddingBackend` returning deterministic 8-dimensional vectors.
- **Always** pass `cache_dir=tmp_path` to `SimilarPlanService` in tests — the real embedding cache (1536-dim) will cause a dimension mismatch with the 8-dim stub backend.

`tests/test_llm_integration.py` makes real OpenAI calls and is `pytest.mark.skipif`-ed unless `OPENAI_API_KEY` is set.

```bash
uv run pytest -v                   # all tests, no API key needed
uv run pytest -v tests/test_end_to_end_graph.py   # full graph with fakes
```

---

## UI (`ui/app.py`)

```bash
uv run streamlit run ui/app.py
```

- Domain selector in sidebar (auto-populated from `config/domains/*.yaml`).
- Streams each node's output as the graph runs.
- Retrieval results: narrative summary shown inline; raw `Data:` JSON shown in a collapsed "Raw data" expander with syntax highlighting (prevents the JSON from breaking the layout).
- Result truncation: non-`Data:` results over 300 chars are truncated with `…`.

---

## Known quirks and past pitfalls

**Retrieval API `request_id` must be a UUID in two places.** Using a non-UUID string or putting it only in the body returns empty results silently. See `retrieval_service.py:HttpRetrievalClient.query()`.

**Stale embedding cache.** If you change the corpus and tests start failing with `ValueError: matmul size X is different from Y`, the cache file under `corpus/.cache/` is stale. It auto-invalidates on corpus content change, but the hash key uses corpus text — if you move/rename entries without changing text, it won't detect the change.

**TABLE_DESCRIPTION.csv is present but not used.** The three main fact tables use `_DATA` suffix in TABLE_DESCRIPTION but `_FACT` suffix in COLUMN_DESCRIPTION, so table/column names couldn't be joined reliably. Decision: skip table descriptions entirely; column descriptions are sufficient context.

**Planner over-selecting KPIs.** If you touch the Planner prompt, watch for the model reverting to dumping all KPIs in one question. The SELF-CHECKS section enforces "no more than ~4-5 KPIs unless the probe genuinely requires all of them."

**Planner generating analytical questions.** The retrieval service is a data fetcher, not an analyst. If questions like "Compare X vs Y" or "Which brand performed best?" slip through, the API will still return data but the NLP extraction may not match the intent. The SCOPE BOUNDARIES section says: "Always phrase questions as data-fetch requests, not as analytical or comparative tasks."

**Planner generating context-dependent questions.** The retrieval service receives each question in complete isolation — it has no memory of prior questions and no shared context. Questions like "What is the power of the same brand in the prior period?" or "same as above but for awareness" will fail to extract parameters correctly. Every question must be fully self-contained: brand, country, period, and all other dimension values must be spelled out explicitly in the question text itself. The SELF-CONTAINED QUESTIONS principle and a corresponding SELF-CHECK in the Planner prompt enforce this.

**Duplicate probes in subsequent rounds.** Fixed by two-layer deduplication: LLM sees `asked_questions` in payload; service deterministically skips any question already in the set. If you see duplicates, check that `evidence_ledger` is being passed through state correctly in `nodes.py:make_planner_node`.

---

## Super-Agent (Unified Domain)

The super-agent in `src/unified_domain/` orchestrates multiple single-domain agents to answer **cross-domain** business questions (e.g., "How did Brahma perform in Brazil in Q1 2026 across perception and consumption?"). It is purely additive — **nothing in `src/ic_agent/` was modified**.

### Architecture (mirrors the single-agent 7-node loop)

```
START → Unified Similar Plan → Unified Planner Consultant → Domain Router
      → Domain Agent Executor (parallel sub-agent runs via asyncio.gather)
      → Unified Decision Consultant → Unified Decision Engine
      ──(continue)──→ Unified Planner Consultant
      ──(stop)──────→ Unified Synthesizer → END
```

**Two key substitutions vs. single-agent:**

| Single-agent node | Super-agent equivalent | Difference |
|---|---|---|
| **Planner** (KPI selection) | **Domain Router** | LLM that assigns each probe candidate to one or more sub-domains and writes a self-contained `scoped_question`. Sees only domain `display_name` + `datasets` descriptions — no KPI knowledge. |
| **Execution** (HTTP retrieval) | **Domain Agent Executor** | For each `DomainProbe`, builds a fresh single-agent graph via `build_app(domain_config, settings)` and runs `await app.ainvoke(...)`. All probes dispatched concurrently via `asyncio.gather`. The sub-agent's `final_answer.markdown` becomes one `UnifiedEvidenceLedgerEntry.result`; the sub-agent's internal `evidence_ledger` is preserved under `sub_evidence`. |

### Zero-shot prompts (strict constraint)

Every super-agent LLM component uses a **zero-shot SYSTEM_PROMPT**: no domain names, no KPI references, no dataset specifics in the static prompt. Domain context comes only via the human message payload:
- `available_domains` — list of registered sub-domains (id, display_name, dataset descriptions)
- `domain_knowledge_doc` — `docs/metadata/unified_domain/knowledge_doc.md`, a KPI-free consolidated overview of every sub-domain and how they relate

The Unified Planner Consultant is instructed to reason about **domain-knowledge-based probes** (what kinds of business questions each sub-domain can answer) — *not* about specific KPIs. KPI selection stays inside each sub-agent's own Planner (unchanged).

### File layout

```
src/unified_domain/
├── models/
│   ├── state.py                          # UnifiedAgentState
│   ├── evidence.py                       # UnifiedEvidenceLedgerEntry (with source_domain_id, sub_evidence)
│   ├── domain_router.py                  # DomainProbe, DomainAssignment, DomainRouterInput/Output
│   ├── planner_consultant.py             # UnifiedPlannerConsultantInput/Output
│   └── decision_consultant.py            # UnifiedDecisionConsultantInput/Output
├── prompts/                              # all zero-shot SYSTEM_PROMPT constants
│   ├── planner_consultant.py
│   ├── domain_router.py
│   ├── decision_consultant.py
│   ├── decision_engine.py
│   └── synthesizer.py
├── services/
│   ├── planner_consultant_service.py
│   ├── domain_router_service.py          # LLM-backed domain assignment + dedup
│   ├── domain_agent_executor.py          # async parallel sub-agent runner (execute / execute_sync)
│   ├── decision_consultant_service.py
│   ├── decision_engine_service.py        # converts unified models → single-agent models to reuse IVF logic
│   └── synthesizer_service.py
├── graph/
│   ├── build_graph.py                    # wires unified StateGraph
│   ├── nodes.py                          # make_*_node factories
│   └── edges.py                          # route_after_decision_engine
└── main.py                               # ic-agent-unified CLI

config/unified_probe_budget.yaml          # super-agent budget
docs/metadata/unified_domain/knowledge_doc.md  # consolidated KPI-free doc
ui/unified_app.py                         # Streamlit UI
tests/unified/                            # 18 tests (unit + end-to-end + integration)
```

### Parallel execution

`DomainAgentExecutor.execute()` is `async` and uses `asyncio.gather(*[run_one(a) for a in assignments])` to dispatch all `DomainAssignment`s concurrently. Within a single assignment, probes for the same domain run sequentially (one sub-agent at a time per domain). Different domains run in true parallel.

A sync wrapper `execute_sync()` is provided because LangGraph nodes are sync — it uses `asyncio.run()` or `asyncio.new_event_loop()` depending on context.

**Failure handling:** if a sub-agent raises an exception, it's caught and an evidence entry with the error message as `result` is returned — the super-agent continues with successful entries.

### Probe budget (separate from single-agent)

```yaml
# config/unified_probe_budget.yaml
probe_budget:
  max_rounds: 2
  max_probes_per_round: 3
  max_total_probes: 5
```

A super-agent "probe" = one sub-agent invocation (which is itself a full multi-round investigation with its own 3/5/8 budget). Worst case: 5 × 8 = 40 retrieval API calls per super-agent run.

### Decision Engine reuse

`UnifiedDecisionEngineService` converts unified models → single-agent models internally so it can call the existing `DecisionEngineService` logic verbatim. The IVF scoring formula is domain-agnostic; only the input shape needed adapting.

### Forward-reference quirk

`DomainRouterInput` in `models/domain_router.py` uses `from __future__ import annotations` to avoid a circular import with `UnifiedPlannerConsultantOutput`. Don't remove that import.

### CLI + UI

```bash
uv run ic-agent-unified --query "How did Brahma perform in Brazil in Q1 2026 across perception and consumption?"
uv run streamlit run ui/unified_app.py
```

The CLI auto-discovers all `config/domains/*.yaml` files as candidate sub-domains. The UI streams each super-agent node's output and surfaces both the unified ledger and each sub-agent's internal evidence in collapsible sections.

### Tests

All 18 unified tests pass without `OPENAI_API_KEY` using `FakeStructuredChatModel`. Integration tests in `tests/unified/test_unified_integration.py` make real OpenAI calls and skip without the key.

```bash
uv run pytest -v tests/unified/          # super-agent only
uv run pytest -v                         # all 56 tests (38 single-agent + 18 super-agent)
```

The Domain Agent Executor tests mock `build_app()` to return a fake compiled graph that asynchronously returns a canned `final_state` — this avoids running real sub-agents during unit tests.

### Interactive flow diagram

Open `docs/unified_flow_diagram.html` in a browser. Mirrors `docs/flow_diagram.html` structure: 9 SVG nodes (input/output + 7 pipeline nodes), pink loop edge, green stop edge, plus a magenta dashed edge for the parallel sub-agent dispatch from Domain Router → Domain Agent Executor. Click any node for input/output/prompt details.

---

## Adding a new usecase

1. Add the usecase ID to `Usecase` literal in `models/retrieval.py`.
2. Add the template name mapping to `_USECASE_TEMPLATE_MAP` in `retrieval_service.py`.
3. Add the usecase ID to `_USECASE_IDS` tuple in `config/usecase_docs.py`.
4. Create `docs/metadata/<domain_id>/knowledge_doc.md` with the knowledge doc. Set `primary_usecase: <usecase_id>` in the domain YAML so it loads under the right key.

---

## Key files to read for context

In roughly priority order for understanding the system:

1. `docs/archetecture.md` — original design spec; everything was built to match this
2. `src/ic_agent/prompts/base.py` — how prompts are assembled
3. `src/ic_agent/prompts/planner.py` — most behaviourally complex prompt
4. `src/ic_agent/services/planner_service.py` — KPI routing + dedup logic
5. `src/ic_agent/graph/build_graph.py` — how everything is wired together
6. `src/ic_agent/services/retrieval_service.py` — the API contract (read the `_extract_answer` method)
7. `docs/metadata/gai_copilot_marketing_brand_guidance_ghq/question_format.md` — the KPI oracle
