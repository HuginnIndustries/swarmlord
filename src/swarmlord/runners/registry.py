"""Runner profile -> runner instance resolution."""

from __future__ import annotations

from swarmlord.core.errors import SwarmLordError
from swarmlord.runners.base import Runner
from swarmlord.runners.claude_code import ClaudeCodeInteractiveRunner
from swarmlord.runners.manual import ManualRunner
from swarmlord.runners.sandcastle import SandcastleDockerRunner


class RunnerRegistry:
    """Holds the set of runners the orchestrator knows how to dispatch to."""

    def __init__(self, runners: list[Runner]) -> None:
        self._runners = list(runners)

    def register(self, runner: Runner) -> None:
        self._runners.append(runner)

    def resolve(self, profile: str) -> Runner:
        for runner in self._runners:
            if runner.can_handle(profile):
                return runner
        known = ", ".join(sorted(r.name for r in self._runners))
        raise SwarmLordError(f"no runner registered for profile '{profile}' (known: {known})")

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._runners)


def default_registry() -> RunnerRegistry:
    """Built-in V1 runners: manual, interactive Claude Code, Sandcastle."""
    return RunnerRegistry(
        [
            ManualRunner(),
            ClaudeCodeInteractiveRunner(),
            SandcastleDockerRunner(),
        ]
    )


def resolve_runner(profile: str) -> Runner:
    """Convenience: resolve a profile against the default registry."""
    return default_registry().resolve(profile)
