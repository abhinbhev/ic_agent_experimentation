"""Loads retrieval usecase knowledge docs for the Planner.

Each file in ``base_dir`` named ``<usecase_id>.md`` becomes one entry in
the returned mapping, keyed by usecase id (see
``ic_agent.models.retrieval.Usecase``). Missing files are simply omitted.
"""

from pathlib import Path

from ic_agent.models.retrieval import Usecase

_USECASE_IDS: tuple[Usecase, ...] = ("brand_guidance", "category")


def load_usecase_docs(base_dir: str = "docs/metadata") -> dict[str, str]:
    base = Path(base_dir)
    docs: dict[str, str] = {}
    for usecase_id in _USECASE_IDS:
        path = base / f"{usecase_id}.md"
        if path.exists():
            docs[usecase_id] = path.read_text(encoding="utf-8")
    return docs
