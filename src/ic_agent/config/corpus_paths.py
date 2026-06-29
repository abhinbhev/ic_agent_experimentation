"""Resolve which similar-plan corpus to load.

We support a per-domain corpus directory convention while keeping the
legacy single-file fallback for environments that haven't migrated.

Resolution order:

* Single-agent (per-domain): ``corpus/<domain_id>/similar_plans.yaml``
  -> fall back to ``settings.corpus_path``.
* Unified super-agent:       ``corpus/unified/similar_plans.yaml``
  -> fall back to ``settings.corpus_path``.

The fallback keeps existing setups working even if the new per-domain
files aren't present.
"""

from __future__ import annotations

from pathlib import Path


def _corpus_root_from_settings_path(legacy_path: str | Path) -> Path:
    """Return the directory that holds per-domain corpus subdirs.

    By convention the legacy path is ``corpus/similar_plans.yaml`` so
    the root is its parent. If the legacy path is something else, we
    still treat its parent as the corpus root.
    """
    return Path(legacy_path).parent


def resolve_domain_corpus_path(domain_id: str, legacy_path: str | Path) -> Path:
    """Path to a single-domain similar-plan corpus, with fallback."""
    root = _corpus_root_from_settings_path(legacy_path)
    candidate = root / domain_id / "similar_plans.yaml"
    if candidate.exists():
        return candidate
    return Path(legacy_path)


def resolve_unified_corpus_path(legacy_path: str | Path) -> Path:
    """Path to the unified super-agent's similar-plan corpus, with fallback."""
    root = _corpus_root_from_settings_path(legacy_path)
    candidate = root / "unified" / "similar_plans.yaml"
    if candidate.exists():
        return candidate
    return Path(legacy_path)
