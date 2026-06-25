"""Loads retrieval usecase knowledge docs and schema metadata for the Planner.

Per-domain metadata lives under ``docs/metadata/<domain_id>/``:

- ``knowledge_doc.md`` -- free-form knowledge doc describing what the
  ``brand_guidance`` usecase covers (and doesn't) for this domain. If
  present, it becomes the ``"brand_guidance"`` entry of ``usecase_docs``.
- ``<usecase_id>.md`` -- a domain-specific override for any other usecase
  doc, falling back to ``docs/metadata/<usecase_id>.md`` (global, shared
  across domains) if no domain-specific version exists.
- ``COLUMN_DESCRIPTION.csv`` -- column descriptions, rendered by
  ``load_schema_doc`` into a markdown summary grouped by table.
- ``question_format.md`` -- retrieval service input-selection guide: valid
  KPI names, parameter extraction rules, and worked examples. Loaded by
  ``load_question_format_doc`` and passed to the Planner so it can form
  questions the retrieval service can execute.

Missing files are simply omitted -- all loaders return empty/``None``
when no metadata exists for a domain.
"""

import csv
from pathlib import Path

from ic_agent.models.retrieval import Usecase

_USECASE_IDS: tuple[Usecase, ...] = ("brand_guidance", "category")


def load_usecase_docs(
    domain_id: str,
    base_dir: str = "docs/metadata",
    primary_usecase: str = "brand_guidance",
) -> dict[str, str]:
    base = Path(base_dir)
    domain_dir = base / domain_id
    docs: dict[str, str] = {}

    knowledge_doc = domain_dir / "knowledge_doc.md"
    if knowledge_doc.is_file():
        docs[primary_usecase] = knowledge_doc.read_text(encoding="utf-8")

    for usecase_id in _USECASE_IDS:
        if usecase_id in docs:
            continue
        for path in (domain_dir / f"{usecase_id}.md", base / f"{usecase_id}.md"):
            if path.is_file():
                docs[usecase_id] = path.read_text(encoding="utf-8")
                break

    return docs


def load_schema_doc(domain_id: str, base_dir: str = "docs/metadata") -> str | None:
    """Render COLUMN_DESCRIPTION.csv into a markdown summary of available
    tables and their columns, grouped by table.

    Returns ``None`` if the file doesn't exist for this domain.
    """
    column_csv = Path(base_dir) / domain_id / "COLUMN_DESCRIPTION.csv"
    if not column_csv.is_file():
        return None

    columns_by_table: dict[str, list[tuple[str, str]]] = {}
    with column_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            columns_by_table.setdefault(row["table_name"], []).append(
                (row["column_name"], row["column_description"])
            )

    lines: list[str] = []
    for table_name, columns in columns_by_table.items():
        lines.append(f"### {table_name}")
        for column_name, column_description in columns:
            lines.append(f"- `{column_name}`: {column_description}")
        lines.append("")

    return "\n".join(lines).strip()


def load_question_format_doc(domain_id: str, base_dir: str = "docs/metadata") -> str | None:
    """Load the retrieval service's question format guide for this domain.

    Returns ``None`` if ``question_format.md`` doesn't exist for this domain.
    """
    path = Path(base_dir) / domain_id / "question_format.md"
    return path.read_text(encoding="utf-8") if path.is_file() else None
