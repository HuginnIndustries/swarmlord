"""Atomic packet writes.

All writes use the temp-file-and-rename pattern: build content in memory,
write to a temp file in the *same* directory (so ``os.replace`` is atomic
on the same filesystem), then rename.

When multiple files must change together (e.g. ``status.yaml`` +
``THREAD_LOG.md`` + ``projects/INDEX.md``), the orchestrator stages the new
contents in memory, validates, and only then performs the renames in
sequence. There is no rollback for a partial sequence; ``swarmlord repair``
is the recovery path.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from swarmlord.core.errors import PacketWriteError
from swarmlord.core.models import PacketStatus
from swarmlord.packets.reader import dump_status_yaml


def write_text_atomic(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically.

    The temp file is created in the same directory so the ``os.replace`` call
    is a same-filesystem rename (atomic on POSIX and Windows for files that
    don't already exist or that are not currently open).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp_path, target)
    except OSError as exc:
        # Clean up the temp file if rename failed.
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise PacketWriteError(f"could not write {target}: {exc}") from exc


def write_status(packet_root: Path, status: PacketStatus) -> None:
    """Serialize a :class:`PacketStatus` and write it atomically."""
    target = packet_root / "workflow" / "status.yaml"
    write_text_atomic(target, dump_status_yaml(status))
