"""Tests for the corpus path resolver."""

from __future__ import annotations

from pathlib import Path

from ic_agent.config.corpus_paths import (
    resolve_domain_corpus_path,
    resolve_unified_corpus_path,
)


def _make_corpus_tree(root: Path, domain_id: str | None = None, unified: bool = False) -> Path:
    legacy = root / "similar_plans.yaml"
    legacy.write_text("- id: legacy\n  intent: legacy\n", encoding="utf-8")
    if domain_id:
        d = root / domain_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "similar_plans.yaml").write_text("- id: dom\n  intent: dom\n", encoding="utf-8")
    if unified:
        u = root / "unified"
        u.mkdir(parents=True, exist_ok=True)
        (u / "similar_plans.yaml").write_text("- id: uni\n  intent: uni\n", encoding="utf-8")
    return legacy


def test_resolve_domain_corpus_prefers_per_domain_file(tmp_path):
    legacy = _make_corpus_tree(tmp_path, domain_id="my_domain")
    resolved = resolve_domain_corpus_path("my_domain", legacy)
    assert resolved == tmp_path / "my_domain" / "similar_plans.yaml"


def test_resolve_domain_corpus_falls_back_to_legacy(tmp_path):
    legacy = _make_corpus_tree(tmp_path)
    resolved = resolve_domain_corpus_path("unknown_domain", legacy)
    assert resolved == legacy


def test_resolve_unified_corpus_prefers_unified_dir(tmp_path):
    legacy = _make_corpus_tree(tmp_path, unified=True)
    resolved = resolve_unified_corpus_path(legacy)
    assert resolved == tmp_path / "unified" / "similar_plans.yaml"


def test_resolve_unified_corpus_falls_back_to_legacy(tmp_path):
    legacy = _make_corpus_tree(tmp_path)
    resolved = resolve_unified_corpus_path(legacy)
    assert resolved == legacy
