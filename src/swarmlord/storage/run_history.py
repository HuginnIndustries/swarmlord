"""SQLite-backed run history.

Three tables:

* ``runs`` — one row per dispatch.
* ``gate_evaluations`` — one row per predicate that ran during a promotion.
* ``transitions`` — one row per stage transition (forward or back).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from swarmlord.core.gates import GateResult
from swarmlord.core.models import RunRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    packet_slug TEXT NOT NULL,
    runner_profile TEXT NOT NULL,
    phase TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    prompt_hash TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    exit_code INTEGER,
    completion_signal_seen TEXT,
    log_path TEXT,
    transcript_path TEXT,
    error TEXT,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_packet ON runs(packet_slug, started_at);

CREATE TABLE IF NOT EXISTS gate_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    packet_slug TEXT NOT NULL,
    predicate TEXT NOT NULL,
    passed INTEGER NOT NULL,
    message TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_slug TEXT NOT NULL,
    from_stage TEXT NOT NULL,
    to_stage TEXT NOT NULL,
    at TEXT NOT NULL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_transitions_packet ON transitions(packet_slug, at);
"""


def default_db_path() -> Path:
    """Resolve the default SQLite path for the current OS.

    Uses ``os.name`` rather than ``sys.platform`` because mypy narrows
    the latter at type-check time on Windows, which marks the POSIX
    branch as unreachable. ``os.name`` is opaque to that narrowing.
    """
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "swarmlord" / "runs.db"
    xdg = os.environ.get("XDG_DATA_HOME")
    base_p = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base_p / "swarmlord" / "runs.db"


class RunHistory:
    """Thin sqlite3 wrapper. All write paths use a single connection per call."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert_run(self, run: RunRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs(
                    id, packet_slug, runner_profile, phase, attempt, prompt_hash,
                    started_at, ended_at, exit_code, completion_signal_seen,
                    log_path, transcript_path, error, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.packet_slug,
                    run.runner_profile,
                    run.phase.value,
                    run.attempt,
                    run.prompt_hash,
                    run.started_at.isoformat(),
                    run.ended_at.isoformat() if run.ended_at else None,
                    run.exit_code,
                    run.completion_signal_seen,
                    str(run.log_path) if run.log_path else None,
                    str(run.transcript_path) if run.transcript_path else None,
                    run.error,
                    run.status,
                ),
            )

    def list_runs(self, packet_slug: str, *, limit: int = 50) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM runs WHERE packet_slug = ? ORDER BY started_at DESC LIMIT ?",
                (packet_slug, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def record_gate_evaluations(
        self,
        packet_slug: str,
        results: list[GateResult],
        *,
        run_id: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO gate_evaluations(
                    run_id, packet_slug, predicate, passed, message, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (run_id, packet_slug, r.label, 1 if r.passed else 0, r.message, now)
                    for r in results
                ],
            )

    def record_transition(
        self,
        packet_slug: str,
        from_stage: str,
        to_stage: str,
        *,
        reason: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transitions(packet_slug, from_stage, to_stage, at, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (packet_slug, from_stage, to_stage, now, reason),
            )

    def list_transitions(self, packet_slug: str) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM transitions WHERE packet_slug = ? ORDER BY at",
                (packet_slug,),
            ).fetchall()
            return [dict(r) for r in rows]
