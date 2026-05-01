"""projects/INDEX.md upsert/read."""

from __future__ import annotations

from pathlib import Path

from swarmlord.packets.index import IndexEntry, read_index, upsert_index_entry


def test_upsert_creates(repo_root: Path) -> None:
    upsert_index_entry(repo_root, IndexEntry(slug="2026-05-a", stage="idea", summary="hi"))
    rows = read_index(repo_root)
    assert "2026-05-a" in rows
    assert rows["2026-05-a"].summary == "hi"


def test_upsert_replaces(repo_root: Path) -> None:
    upsert_index_entry(repo_root, IndexEntry(slug="2026-05-a", stage="idea", summary="hi"))
    upsert_index_entry(
        repo_root,
        IndexEntry(slug="2026-05-a", stage="discovery", summary="hi v2"),
    )
    rows = read_index(repo_root)
    assert rows["2026-05-a"].stage == "discovery"
    assert rows["2026-05-a"].summary == "hi v2"


def test_read_missing_returns_empty(tmp_path: Path) -> None:
    assert read_index(tmp_path) == {}
