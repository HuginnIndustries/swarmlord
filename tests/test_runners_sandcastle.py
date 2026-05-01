"""Sandcastle runner — subprocess injected via runner_options."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from swarmlord.core.errors import RunnerError
from swarmlord.core.models import (
    AgentConfig,
    GateConfig,
    WorkflowDefinition,
    WorkflowHooks,
)
from swarmlord.core.phases import Phase
from swarmlord.runners.base import RunRequest
from swarmlord.runners.sandcastle import SandcastleDockerRunner


def _request(tmp_path: Path, *, options: dict[str, object] | None = None) -> RunRequest:
    return RunRequest(
        packet_slug="x",
        packet_root=tmp_path,
        rendered_prompt="hi",
        workflow=WorkflowDefinition(
            runner_profile="sandcastle-docker",
            phase=Phase.BUILD_SPEC,
            hooks=WorkflowHooks(),
            agent=AgentConfig(),
            gates=GateConfig(),
            prompt_template="",
        ),
        runner_options=options or {},
    )


def _summary(payload: dict[str, object]) -> str:
    return f"some logs\n__SANDCASTLE_SUMMARY__{json.dumps(payload)}\n"


def test_happy_path(tmp_path: Path) -> None:
    captured_cmd: list[list[str]] = []

    async def fake(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
        captured_cmd.append(cmd)
        out = _summary(
            {
                "exitCode": 0,
                "completionSignal": "<promise>COMPLETE</promise>",
                "commits": ["abc1234"],
                "transcriptPath": str(cwd / "transcript.jsonl"),
            }
        )
        return 0, out, ""

    runner = SandcastleDockerRunner()
    res = asyncio.run(runner.run(_request(tmp_path, options={"_subprocess_factory": fake})))
    assert res.exit_code == 0
    assert res.completion_signal_seen == "<promise>COMPLETE</promise>"
    assert res.commits == ["abc1234"]
    assert res.transcript_path is not None
    # main.ts and prompt.md were written.
    assert (tmp_path / ".sandcastle" / "main.ts").is_file()
    assert (tmp_path / ".sandcastle" / "prompt.md").read_text() == "hi"
    assert captured_cmd, "subprocess factory was not called"


def test_nonzero_exit_returns_failure(tmp_path: Path) -> None:
    async def fake(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
        return 7, _summary({"exitCode": 7, "completionSignal": None, "commits": []}), "stderr"

    runner = SandcastleDockerRunner()
    res = asyncio.run(runner.run(_request(tmp_path, options={"_subprocess_factory": fake})))
    assert res.exit_code == 7
    assert res.completion_signal_seen is None


def test_missing_summary_with_zero_exit_raises(tmp_path: Path) -> None:
    async def fake(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
        return 0, "no summary line here", ""

    runner = SandcastleDockerRunner()
    with pytest.raises(RunnerError):
        asyncio.run(runner.run(_request(tmp_path, options={"_subprocess_factory": fake})))
