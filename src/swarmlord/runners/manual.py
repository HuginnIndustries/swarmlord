"""Manual runner — render the prompt, optionally copy to clipboard, return.

This is the v1 happy-path runner: no agent invocation, the orchestrator
just hands the prompt back to the human to paste into Claude Code or Codex.

When ``clipboard=True`` and the clipboard backend is unavailable, the
runner falls back to stdout *and* invokes ``warn_writer`` so the caller can
surface a visible "clipboard unavailable" message — silent fallback masks
the user's intent.
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
        warn_writer: Callable[[str], None] | None = None,
    ) -> None:
        self._clipboard = clipboard
        self._clipboard_writer = clipboard_writer
        self._stdout_writer = stdout_writer or (lambda s: sys.stdout.write(s))
        self._warn_writer = warn_writer

    def can_handle(self, profile: str) -> bool:
        return profile == self.name

    async def run(self, request: RunRequest) -> RunResult:
        started = datetime.now(UTC)
        wrote_clipboard = False
        clipboard_error: str | None = None
        if self._clipboard:
            wrote_clipboard, clipboard_error = self._copy_to_clipboard(request.rendered_prompt)
        if not wrote_clipboard:
            if self._clipboard and clipboard_error and self._warn_writer is not None:
                self._warn_writer(f"clipboard unavailable, printing instead: {clipboard_error}")
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

    def _copy_to_clipboard(self, text: str) -> tuple[bool, str | None]:
        if self._clipboard_writer is not None:
            try:
                self._clipboard_writer(text)
            except Exception as exc:
                return False, str(exc)
            return True, None
        try:
            import pyperclip

            pyperclip.copy(text)
        except Exception as exc:
            return False, str(exc)
        return True, None
