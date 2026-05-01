"""Read and update ``projects/INDEX.md``.

The index is a markdown table of every packet's slug, stage, summary, and
extracted destination (if any). The orchestrator keeps it in sync on
``new``, ``promote``, and ``extract``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from swarmlord.packets.writer import write_text_atomic

_HEADER = "# Projects Index\n\nThis file lists every packet under `projects/` with its current stage and a short summary.\n"

_TABLE_HEADER = "| Slug | Stage | Summary | Extracted To |\n| --- | --- | --- | --- |\n"

_ROW_RE = re.compile(
    r"^\|\s*(?P<slug>[^|]+?)\s*\|\s*(?P<stage>[^|]+?)\s*\|\s*(?P<summary>[^|]*?)\s*\|\s*(?P<extracted>[^|]*?)\s*\|\s*$",
    re.MULTILINE,
)


@dataclass(slots=True)
class IndexEntry:
    slug: str
    stage: str
    summary: str = ""
    extracted_to: str = ""


@dataclass(slots=True)
class _Index:
    entries: dict[str, IndexEntry] = field(default_factory=dict)


def read_index(repo_root: Path, *, projects_subdir: str = "projects") -> dict[str, IndexEntry]:
    """Parse ``projects/INDEX.md`` into a slug-keyed dict of entries."""
    index_path = repo_root / projects_subdir / "INDEX.md"
    if not index_path.is_file():
        return {}
    text = index_path.read_text(encoding="utf-8")
    entries: dict[str, IndexEntry] = {}
    for m in _ROW_RE.finditer(text):
        slug = m.group("slug").strip()
        if slug.lower() in {"slug", "---"}:
            continue
        entries[slug] = IndexEntry(
            slug=slug,
            stage=m.group("stage").strip(),
            summary=m.group("summary").strip(),
            extracted_to=m.group("extracted").strip(),
        )
    return entries


def upsert_index_entry(
    repo_root: Path,
    entry: IndexEntry,
    *,
    projects_subdir: str = "projects",
) -> None:
    """Insert or update one row in ``projects/INDEX.md`` and rewrite atomically."""
    index_path = repo_root / projects_subdir / "INDEX.md"
    entries = read_index(repo_root, projects_subdir=projects_subdir)
    entries[entry.slug] = entry
    rendered = _render_index(entries)
    write_text_atomic(index_path, rendered)


def _render_index(entries: dict[str, IndexEntry]) -> str:
    body = _HEADER + "\n" + _TABLE_HEADER
    for slug in sorted(entries):
        e = entries[slug]
        body += f"| {e.slug} | {e.stage} | {e.summary} | {e.extracted_to} |\n"
    return body
