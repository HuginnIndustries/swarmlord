"""Interactive Claude Code runner — spawns the ``claude`` CLI in the packet root.

The runner pipes the rendered prompt as the initial input and returns when
the process exits. This runner is intentionally not covered by the V1 unit
tests (it requires the real ``claude`` binary); a manual smoke test is the
acceptance path.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime

from swarmlord.core.errors import RunnerError
from swarmlord.runners.base import RunRequest, RunResult


class ClaudeCodeInteractiveRunner:
    """Spawn ``claude`` (the CLI binary) interactively against the packet root."""

    name: str = "claude-code-interactive"

    def can_handle(self, profile: str) -> bool:
        return profile == self.name

    async def run(self, request: RunRequest) -> RunResult:  # pragma: no cover - smoke only
        binary = shutil.which("claude")
        if binary is None:
            raise RunnerError("`claude` CLI not found on PATH")
        started = datetime.now(UTC)
        proc = await asyncio.create_subprocess_exec(
            binary,
            cwd=str(request.packet_root),
            stdin=asyncio.subprocess.PIPE,
            stdout=None,
            stderr=None,
        )
        assert proc.stdin is not None
        proc.stdin.write(request.rendered_prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()
        exit_code = await proc.wait()
        ended = datetime.now(UTC)
        return RunResult(
            runner=self.name,
            started_at=started,
            ended_at=ended,
            exit_code=exit_code,
        )
