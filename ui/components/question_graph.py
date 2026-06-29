"""Streamlit wrapper for the live question-graph HTML component."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_HERE = Path(__file__).resolve().parent
_TEMPLATE_PATH = _HERE / "question_graph.html"


def render_question_graph(
    tree: dict[str, Any] | None,
    *,
    height: int = 800,
    key: str | None = "qgraph",
) -> None:
    """Render the live question graph for a given tree snapshot.

    Pass ``None`` for ``tree`` to show the empty state.
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    tree_json = json.dumps(tree) if tree is not None else "null"
    html = template.replace("__TREE_JSON__", tree_json)
    components.html(html, height=height, scrolling=False)
    # ``key`` is accepted for API symmetry but components.html doesn't take one
    _ = key  # silence linters
    _ = st  # keep import for future state needs
