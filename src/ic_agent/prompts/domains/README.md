# Per-domain prompt guidelines

This folder holds optional, free-form domain-specific guidance that is
appended to the dynamic `domain_prompt` for a given domain and service
(use case).

Layout:

```
prompts/domains/<domain_id>/<service_key>.md
```

- `<domain_id>` matches `DomainConfig.domain_id` (i.e. `config/domains/<domain_id>.yaml`).
- `<service_key>` is one of: `planner_consultant`, `planner`,
  `decision_consultant`, `decision_engine`, `synthesizer`.

If a file exists for a given `(domain_id, service_key)` pair, its contents
are appended to that service's `domain_prompt` (after the generic catalogue
rendered from the domain config and any `domain_prompt_overrides`). See
`prompts/base.py::get_prompt_bundle` and `PromptBundle.render`.

Create a file here only when a domain/service combination needs guidance
beyond the generic catalogue (e.g. how to interpret a domain's terminology
for a specific use case, or worked examples for that domain). Leave absent
otherwise -- there is no requirement for every domain/service pair to have
one.
