"""Runner implementations + the resolution registry."""

from __future__ import annotations

from swarmlord.runners.base import Runner, RunRequest, RunResult
from swarmlord.runners.claude_code import ClaudeCodeInteractiveRunner
from swarmlord.runners.manual import ManualRunner
from swarmlord.runners.registry import RunnerRegistry, default_registry, resolve_runner
from swarmlord.runners.sandcastle import SandcastleDockerRunner

__all__ = [
    "ClaudeCodeInteractiveRunner",
    "ManualRunner",
    "RunRequest",
    "RunResult",
    "Runner",
    "RunnerRegistry",
    "SandcastleDockerRunner",
    "default_registry",
    "resolve_runner",
]
