"""Manual runner — render the prompt, optionally copy to clipboard, return.

This is the v1 happy-path runner: no agent invocation, the orchestrator
just hands the prompt back to the human to paste into Claude Code or Codex.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from swarmlord.runners.base import RunRequest, RunResult

if TYPE_CHECKING:  # pragma: no cover - import only used for typing
    from collections.abc import Callable


class ManualRunner:
    """Synchronous-style runner exposed via the async :class:`Runner` protocol."""

    name: str = "manual"

    def __init__(
        self,
        *,
        clipboard: bool = True,
        clipboard_writer: Callable[[str], None] | None = None,
        stdout_writer: Callable[[str], None] | None = None,
    ) -> None:
        self._clipboard = clipboard
        self._clipboard_writer = clipboard_writer
        self._stdout_writer = stdout_writer or (lambda s: sys.stdout.write(s))

    def can_handle(self, profile: str) -> bool:
        return profile == self.name

    async def run(self, request: RunRequest) -> RunResult:
        started = datetime.now(UTC)
        wrote_clipboard = False
        if self._clipboard:
            wrote_clipboard = self._copy_to_clipboard(request.rendered_prompt)
        if not wrote_clipboard:
            self._stdout_writer(request.rendered_prompt)
            if not request.rendered_prompt.endswith("\n"):
                self._stdout_writer("\n")
        ended = datetime.now(UTC)
        return RunResult(
            runner=self.name,
            started_at=started,
            ended_at=ended,
            exit_code=0,
            completion_signal_seen=None,
        )

    def _copy_to_clipboard(self, text: str) -> bool:
        if self._clipboard_writer is not None:
            try:
                self._clipboard_writer(text)
                return True
            except Exception:
                return False
        try:
            import pyperclip

            pyperclip.copy(text)
            return True
        except Exception:
            return False
