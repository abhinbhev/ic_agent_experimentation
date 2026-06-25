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

The only live domain in production use is `gai_copilot_marketing_brand_guidance_ghq` — brand health / perception data from the `analysis_template_svc` retrieval API.

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
│   ├── probe_budget.yaml              # budget limits, score-fusion weights, IVF weights
│   └── domains/
│       ├── gai_copilot_marketing_brand_guidance_ghq.yaml   # LIVE domain (deliberately minimal)
│       └── example.yaml               # toy domain for testing
│
├── corpus/
│   └── similar_plans.yaml             # investigation archetype corpus for SimilarPlanService
│
├── docs/
│   ├── archetecture.md                # original architecture spec (primary reference)
│   ├── prompt_of_prompts.md           # prompt design guide (style reference)
│   ├── flow_diagram.html              # interactive HTML flow diagram (open in browser)
│   ├── brand highlights refined.pdf   # real run output PDF (used to populate the worked example)
│   ├── brand_highlights_extracted.md  # OCR text of the above PDF
│   └── metadata/
│       └── gai_copilot_marketing_brand_guidance_ghq/
│           ├── knowledge_doc.md       # brand_guidance usecase knowledge doc (fed to Planner)
│           ├── question_format.md     # retrieval NLP extraction guide (fed to Planner — critical)
│           ├── COLUMN_DESCRIPTION.csv # column-level schema fed to Planner
│           └── TABLE_DESCRIPTION.csv  # NOT used (user decision: columns are sufficient)
│
├── src/ic_agent/
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
├── tests/
│   ├── conftest.py                    # FakeStructuredChatModel, fixtures, stub embeddings
│   ├── test_config.py
│   ├── test_planner_service.py
│   ├── test_similar_plan_service.py
│   ├── test_usecase_docs.py
│   ├── test_planner_service.py
│   ├── test_end_to_end_graph.py
│   └── test_llm_integration.py        # skipped without OPENAI_API_KEY
│
└── ui/
    └── app.py                         # Streamlit UI (uv run streamlit run ui/app.py)
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
- pattern_id: brand_country_period_performance
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

**Coverage subsumption:** Before generating a question for probe N, check whether any question already assigned to an earlier probe in this batch already returns a superset of what probe N needs. If so, set `questions=[]` for probe N and note the subsumption in `reason`.

**Multi-KPI grouping:** The retrieval service can handle multiple KPIs in one call. Group related KPIs (e.g. `meaningful, difference, salience`) into one question. Only split into multiple questions when KPIs belong to genuinely distinct retrieval types (e.g. factual KPIs vs `bip_market` imagery) or different dimension cuts (e.g. overall vs demographic breakdown).

**Deduplication (two-layer):**
1. **LLM-level:** `asked_questions` (all questions from prior rounds' evidence ledger) are passed in the JSON payload with explicit instruction not to regenerate them.
2. **Deterministic backstop:** `planner_service.py` skips any generated question whose lowercased form is in `asked_questions`. This is the safety net — the LLM constraint should catch most, but this catches any slippage.

**Output per probe:**
```python
ProbeUsecaseAssignment(
    probe_candidate_id="P1",
    questions=["What is the power of Brahma in Brazil in Q1 2026, Q4 2025, and Q1 2025?"],
    usecase="brand_guidance",
    reason="power captures overall equity; 3-period fetch covers current, prior-quarter, and prior-year."
)
```
`questions` is a list (can be empty if subsumed). Each item becomes one `ToolCall`.

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
4. `incremental_value_below_threshold` — weighted IVF score < `stop_threshold`
5. else: `continue`

**Incremental Value Framework (IVF) scoring:**
```
evidence_coverage      = relevant_probes / total_probes_completed          weight: 0.30
confidence             = decision_consultant confidence score (0-1)         weight: 0.25
remaining_gaps_score   = unresolved_gaps / total_gaps                       weight: 0.20
alt_hypotheses_score   = min(new_hypotheses / 3, 1.0)                      weight: 0.15
probe_cost_score       = max(0, 1 - total_probes / max_total_probes)        weight: 0.10
stop_threshold         = 0.35
```

All weights and the threshold live in `config/probe_budget.yaml` and are runtime-configurable.

---

### Node 7 — Synthesizer (LLM)

**Purpose:** Produces a clean, business-facing markdown report from the full ledger.

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

**Planner is unique:** In addition to `DOMAIN GUIDELINES`, the Planner receives `usecase_docs`, `question_format`, `schema`, and `asked_questions` in the **human message** JSON payload — these are per-request, not per-domain prompt content.

---

## Domain metadata files

All per-domain metadata lives under `docs/metadata/<domain_id>/`:

| File | Purpose | Fed to |
|------|---------|--------|
| `knowledge_doc.md` | What the `brand_guidance` usecase can/can't answer | Planner (as `usecase_docs["brand_guidance"]`) |
| `question_format.md` | Retrieval service NLP extraction guide: valid KPI names, parameter rules, examples | Planner (as `question_format`) |
| `COLUMN_DESCRIPTION.csv` | Column-level schema (`table_name`, `column_name`, `column_description`) | Planner (as `schema`) |
| `TABLE_DESCRIPTION.csv` | Table descriptions — **NOT used** (user decision: column descriptions are sufficient) | — |

**To add a new domain:**
1. Create `config/domains/<domain_id>.yaml` with `DomainConfig` fields.
2. Create `docs/metadata/<domain_id>/` and populate the above files.
3. The domain appears automatically in the UI dropdown and CLI `--domain` arg.

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
  evidence_coverage: 0.30
  confidence: 0.25
  remaining_gaps: 0.20
  alternative_hypotheses: 0.15
  probe_cost: 0.10
  stop_threshold: 0.35
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

## Adding a new usecase

1. Add the usecase ID to `Usecase` literal in `models/retrieval.py`.
2. Add the template name mapping to `_USECASE_TEMPLATE_MAP` in `retrieval_service.py`.
3. Add the usecase ID to `_USECASE_IDS` tuple in `config/usecase_docs.py`.
4. Create `docs/metadata/<domain_id>/<usecase_id>.md` with the knowledge doc.

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
