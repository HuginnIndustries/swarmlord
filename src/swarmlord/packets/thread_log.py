"""Append-only THREAD_LOG.md helper.

Per the project conventions, ``THREAD_LOG.md`` is never rewritten — only
new dated entries are appended. The atomic-write rule still applies (build
the new content in memory, then replace).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from swarmlord.packets.writer import write_text_atomic

_HEADER = "# Thread Log\n\nAppend short handoff entries here. Durable findings belong in `spec/`, not only in this log.\n\n## Entries\n\n"


def append_thread_log(
    packet_root: Path,
    entry: str,
    *,
    when: date | None = None,
) -> None:
    """Append a dated bullet to ``THREAD_LOG.md``, creating the file if needed."""
    log = packet_root / "THREAD_LOG.md"
    today = (when or date.today()).isoformat()
    bullet = f"- {today}: {entry.strip()}\n"
    if log.is_file():
        existing = log.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
        new = existing + bullet
    else:
        new = _HEADER + bullet
    write_text_atomic(log, new)
