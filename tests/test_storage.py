"""SQLite run history."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from swarmlord.core.gates import GateResult
from swarmlord.core.models import FileExists, RunRecord
from swarmlord.core.phases import Phase
from swarmlord.storage.run_history import RunHistory


def _record() -> RunRecord:
    return RunRecord(
        id="r1",
        packet_slug="2026-05-x",
        runner_profile="manual",
        phase=Phase.DISCOVERY,
        attempt=0,
        prompt_hash="deadbeef",
        started_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        exit_code=0,
        status="succeeded",
    )


def test_runs_round_trip(tmp_path: Path) -> None:
    history = RunHistory(tmp_path / "runs.db")
    history.insert_run(_record())
    rows = history.list_runs("2026-05-x")
    assert len(rows) == 1
    assert rows[0]["status"] == "succeeded"


def test_gate_evaluations_inserted(tmp_path: Path) -> None:
    history = RunHistory(tmp_path / "runs.db")
    pred = FileExists(kind="file_exists", path="x.md")
    history.record_gate_evaluations(
        "2026-05-x",
        [GateResult(predicate=pred, passed=True, message="ok")],
    )


def test_transitions_round_trip(tmp_path: Path) -> None:
    history = RunHistory(tmp_path / "runs.db")
    history.record_transition("2026-05-x", "idea", "discovery", reason="manual")
    rows = history.list_transitions("2026-05-x")
    assert len(rows) == 1
    assert rows[0]["from_stage"] == "idea"
    assert rows[0]["to_stage"] == "discovery"
