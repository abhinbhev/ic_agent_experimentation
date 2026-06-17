# Contributing to IC Agent

---

## Getting started

```bash
git clone <repo>
cd ic_agent_experimentation
uv sync --extra dev
cp .env.example .env   # fill in your keys
uv run pre-commit install
```

`uv sync --extra dev` installs `pre-commit`, `detect-secrets`, `pytest`, and `ruff` alongside the main dependencies. `pre-commit install` wires the hooks into your local `.git/` — run it once after cloning and it fires automatically on every commit from then on.

---

## Running tests

```bash
uv run pytest -v                                        # all tests, no API key needed
uv run pytest -v tests/test_end_to_end_graph.py        # full graph with fake LLMs
OPENAI_API_KEY=sk-... uv run pytest tests/test_llm_integration.py   # real API call
```

All 38 unit tests use `FakeStructuredChatModel` and a stub embedding backend — no network required. The integration test auto-skips without `OPENAI_API_KEY`.

When adding a new service or node:
- Add a unit test using `FakeStructuredChatModel` — see `tests/conftest.py` for the fixture pattern.
- Always pass `cache_dir=tmp_path` to `SimilarPlanService` in tests — the real cache uses 1536-dim embeddings; the stub uses 8-dim, and a dimension mismatch will cause a cryptic `matmul` error.

---

## Pre-commit hooks

Hooks run automatically on `git commit`. They cover:

| Hook | What it catches |
|---|---|
| `detect-secrets` | API keys, tokens, passwords, bearer strings |
| `detect-private-key` | RSA/SSH private keys |
| `check-added-large-files` | Files >500KB (accidental PDFs, model weights) |
| `no-commit-to-branch` | Blocks direct commits to `main` — use a branch + PR |
| `check-yaml` | Malformed YAML in `config/` |
| `check-merge-conflict` | Leftover `<<<<<<` markers |
| `ruff` | Lint and format (matches `pyproject.toml` config) |

**If a hook blocks your commit**, it will tell you what it found. Either fix it or, if it's a genuine false positive, update the secrets baseline:

```bash
detect-secrets scan --baseline .secrets.baseline
git add .secrets.baseline
git commit -m "update secrets baseline"
```

**To run hooks manually** (useful before opening a PR):

```bash
uv run pre-commit run --all-files
```

---

## Secrets and `.env`

- **Never commit `.env`** — it is gitignored. Copy `.env.example` and fill in values locally.
- **Never hardcode secrets in source** — use env vars read through `config/settings.py` (pydantic-settings). All env vars have a single source of truth there; nothing reads `os.environ` directly anywhere else.
- `.secrets.baseline` is committed — it records known false positives (dummy test keys, variable names like `SERVICE_KEY`) so the scanner doesn't block on them. If you add new test fixtures with placeholder key strings, regenerate it:

```bash
detect-secrets scan --exclude-files '\.env$' \
  --exclude-files 'docs/brand_highlights_extracted\.md' \
  --exclude-files 'docs/flow_diagram\.html' \
  > .secrets.baseline
git add .secrets.baseline
```

---

## Adding a new domain

1. Create `config/domains/<domain_id>.yaml` with `DomainConfig` fields (see `config/domains/gai_copilot_marketing_brand_guidance_ghq.yaml` as reference).
2. Create `docs/metadata/<domain_id>/` and add:
   - `knowledge_doc.md` — what the usecase covers and doesn't
   - `question_format.md` — retrieval service NLP extraction guide; valid KPI names, parameter rules, worked examples. **This is the Planner's KPI oracle — it must be accurate.**
   - `COLUMN_DESCRIPTION.csv` — columns with `table_name`, `column_name`, `column_description`
3. Add an entry to `corpus/similar_plans.yaml` with a matching `dataset_family`.
4. The domain appears automatically in the UI dropdown and `--domain` CLI arg.

---

## Adding a new retrieval usecase

1. Add the usecase ID to the `Usecase` literal in `src/ic_agent/models/retrieval.py`.
2. Add the template name to `_USECASE_TEMPLATE_MAP` in `src/ic_agent/services/retrieval_service.py`.
3. Add the ID to `_USECASE_IDS` in `src/ic_agent/config/usecase_docs.py`.
4. Create `docs/metadata/<domain_id>/<usecase_id>.md` as the knowledge doc.

---

## Code style

- **Formatter/linter:** `ruff` (runs automatically via pre-commit; config in `pyproject.toml`).
- **No comments explaining what code does** — name things clearly instead. Add a comment only when the *why* is non-obvious (a hidden constraint, a known API quirk, a workaround).
- **No speculative abstractions** — implement what the task requires; don't design for hypothetical future use.
- **Pydantic v2 models for every service boundary** — inputs and outputs are pydantic `BaseModel`s. The LangGraph `AgentState` is a `TypedDict`.
- **All env vars through `config/settings.py`** — no direct `os.environ` reads elsewhere.

---

## Architecture quick reference

Full detail in `CLAUDE.md`. The short version:

```
START → similar_plan → planner_consultant → planner → execution
      → decision_consultant → decision_engine
      ──(continue)──→ planner_consultant   (next round)
      ──(stop)──────→ synthesis → END
```

- **Planner Consultant and Decision Consultant are KPI-agnostic** — they reason in plain business language. Never add KPI names or data-source references to their prompts.
- **Planner questions must be data-fetch requests**, not analytical tasks. "What is the power of all brands in Brazil in Q1 2026?" not "Compare Brahma vs competitors."
- **Retrieval API `request_id` must be a UUID in two places** (URL params AND JSON body) — using a custom string returns empty results silently. See `retrieval_service.py`.
- **Decision Engine stop/continue is fully deterministic** — no LLM involved except for the `recommended_next_gap` text. Do not move stop logic into a prompt.

---

## Prompt changes

Prompts live in `src/ic_agent/prompts/`. Before changing one:

1. Read `docs/prompt_of_prompts.md` for the style guide.
2. Read the existing prompt in full — each has explicit REASONING PROCESS steps, SCOPE BOUNDARIES, and SELF-CHECKS sections. Changes to one section often affect another.
3. Run the end-to-end test after any prompt change: `uv run pytest -v tests/test_end_to_end_graph.py`.
4. The Planner prompt (`prompts/planner.py`) is the most sensitive — watch for KPI over-selection (more than ~4 KPIs per question) and analytical phrasing slipping back in.
