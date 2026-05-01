"""Manual runner — clipboard mocked, stdout fallback verified."""

from __future__ import annotations

import asyncio
from pathlib import Path

from swarmlord.core.models import (
    AgentConfig,
    GateConfig,
    WorkflowDefinition,
    WorkflowHooks,
)
from swarmlord.core.phases import Phase
from swarmlord.runners.base import RunRequest
from swarmlord.runners.manual import ManualRunner


def _request(tmp_path: Path) -> RunRequest:
    return RunRequest(
        packet_slug="x",
        packet_root=tmp_path,
        rendered_prompt="hello prompt",
        workflow=WorkflowDefinition(
            runner_profile="manual",
            phase=Phase.DISCOVERY,
            hooks=WorkflowHooks(),
            agent=AgentConfig(),
            gates=GateConfig(),
            prompt_template="",
        ),
    )


def test_manual_runner_clipboard_path(tmp_path: Path) -> None:
    captured: list[str] = []
    runner = ManualRunner(
        clipboard=True,
        clipboard_writer=captured.append,
        stdout_writer=lambda _: None,
    )
    result = asyncio.run(runner.run(_request(tmp_path)))
    assert result.exit_code == 0
    assert captured == ["hello prompt"]


def test_manual_runner_stdout_fallback(tmp_path: Path) -> None:
    written: list[str] = []
    runner = ManualRunner(
        clipboard=False,
        stdout_writer=written.append,
    )
    asyncio.run(runner.run(_request(tmp_path)))
    assert "hello prompt" in "".join(written)


def test_manual_runner_clipboard_failure_falls_back(tmp_path: Path) -> None:
    written: list[str] = []

    def _fail(_: str) -> None:
        raise RuntimeError("no clipboard")

    runner = ManualRunner(
        clipboard=True,
        clipboard_writer=_fail,
        stdout_writer=written.append,
    )
    asyncio.run(runner.run(_request(tmp_path)))
    assert "hello prompt" in "".join(written)


def test_manual_runner_can_handle() -> None:
    runner = ManualRunner()
    assert runner.can_handle("manual")
    assert not runner.can_handle("sandcastle-docker")
