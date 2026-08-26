"""CLI tests via Typer's CliRunner."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner

from swarmlord.cli import app
from tests.conftest import make_packet


@contextmanager
def _cd(target: Path) -> Iterator[None]:
    cur = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(cur)


def test_help_lists_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("list", "next", "new", "render", "run", "promote", "validate"):
        assert cmd in result.stdout


def test_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0


def test_list_empty(repo_root: Path) -> None:
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["list"])
    assert result.exit_code == 0
    assert "no packets" in result.stdout


def test_list_renders_packets(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a")
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["list"])
    assert result.exit_code == 0
    assert "2026-05-a" in result.stdout


def test_list_json(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a")
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    assert "2026-05-a" in result.stdout


def test_render_outputs_prompt(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a")
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["render", "2026-05-a"])
    assert result.exit_code == 0
    assert "do the thing" in result.stdout


def test_validate_all_passes(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a")
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["validate", "--all"])
    assert result.exit_code == 0


def test_promote_failing_gate_exits_2(repo_root: Path) -> None:
    from swarmlord.core.stages import Stage

    make_packet(repo_root, slug="2026-05-a", stage=Stage.DISCOVERY)
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["promote", "2026-05-a"])
    assert result.exit_code == 2


def test_next_prints_top_candidate(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a")
    with _cd(repo_root):
        result = CliRunner().invoke(app, ["next"])
    assert result.exit_code == 0
    assert "2026-05-a" in result.stdout


def test_log_command_empty_history(repo_root: Path) -> None:
    """`swarmlord log` against a packet with no recorded runs prints a dim notice."""
    make_packet(repo_root, slug="2026-05-noruns")
    # Point RunHistory at an isolated DB so we don't touch the user's real one.
    db_path = repo_root / "runs.db"
    with _cd(repo_root):
        result = CliRunner().invoke(
            app,
            ["log", "2026-05-noruns"],
            env={"XDG_DATA_HOME": str(db_path.parent)},
        )
    assert result.exit_code == 0
    assert "no history yet" in result.stdout or "2026-05-noruns" in result.stdout
