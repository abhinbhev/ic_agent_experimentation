# IC Agent Experimentation

A LangGraph-based "agentic analytics" framework. An iterative loop of
Planner Consultant -> Planner -> Retrieval Execution -> Decision
Consultant -> Decision Engine refines an investigation plan and gathers
evidence until the Decision Engine decides the marginal value of another
probe round is too low, at which point a Final Answer Synthesizer
produces a markdown report.

The "Consultant" components (Planner Consultant, Decision Consultant) are
domain-agnostic and directional -- they reason about hypotheses, gaps and
probe goals in plain business language, with no knowledge of KPIs,
datasets or dimensions. The Planner and Decision Engine are the
domain-grounded components: the Planner rewrites each probe goal into a
concrete, KPI/dimension-grounded question (using the selected domain's
metrics, datasets, dimensions and terminology) before routing it to a
retrieval usecase, and the Decision Engine's gap recommendation is made
with the same domain context available.

See [docs/archetecture.md](docs/archetecture.md) for the full architecture
and [docs/prompt_of_prompts.md](docs/prompt_of_prompts.md) for prompt-design
guidance.

## Status

All pydantic models, config loading, the Similar Plan Service (BM25 +
embeddings hybrid search), the deterministic Planner and Decision Engine
scoring, and the full LangGraph wiring are implemented. The LLM-backed
services (Planner Consultant, Planner, Decision Consultant, Decision
Engine's gap recommendation, Synthesizer) call OpenAI (directly or via a
LiteLLM proxy) via `with_structured_output`, with real prompts in
`src/ic_agent/prompts/` -- see `src/ic_agent/prompts/base.py` for how each
service's static `SYSTEM_PROMPT` is combined with a dynamic, per-domain
"DOMAIN GUIDELINES" section, and `src/ic_agent/prompts/domains/` for
optional per-domain/per-use-case guideline files.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in OPENAI_API_KEY
```

## Running

```bash
uv run ic-agent --domain example --query "Why did revenue decline in East China during Q1?"
```

## Tests

```bash
uv run pytest -v
```

All unit tests run without `OPENAI_API_KEY` using fake LLMs and a
deterministic stub embedding backend. `tests/test_llm_integration.py`
makes a real OpenAI call and is skipped unless `OPENAI_API_KEY` is set.

## Configuration

- `config/domains/<domain_id>.yaml` - `DomainConfig` (datasets, metrics,
  dimensions, business rules, terminology, prompt overrides).
- `config/probe_budget.yaml` - probe budget limits, score-fusion weights
  for the Similar Plan Service, and the Incremental Value Framework
  weights/threshold used by the Decision Engine.
- `corpus/similar_plans.yaml` - similar-plan archetype corpus searched by
  the Similar Plan Service.

Environment variables (see `.env.example`) configure the OpenAI model,
embedding backend (OpenAI or optional Ollama with automatic fallback),
and file paths.
