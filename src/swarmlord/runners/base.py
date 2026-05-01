"""Runner protocol + RunRequest / RunResult shapes.

Runners are async because real ones (Sandcastle, Claude Code) involve long
subprocess waits. The manual runner is also async to keep the interface
uniform; it just returns immediately.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from swarmlord.core.models import WorkflowDefinition


class RunRequest(BaseModel):
    """Input passed into a runner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    packet_slug: str
    packet_root: Path
    rendered_prompt: str
    workflow: WorkflowDefinition
    runner_options: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Output emitted by a runner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    runner: str
    started_at: datetime
    ended_at: datetime
    exit_code: int
    completion_signal_seen: str | None = None
    log_path: Path | None = None
    transcript_path: Path | None = None
    commits: list[str] = Field(default_factory=list)
    error: str | None = None


@runtime_checkable
class Runner(Protocol):
    """The protocol every runner implements."""

    name: str

    def can_handle(self, profile: str) -> bool:  # pragma: no cover - protocol
        ...

    async def run(self, request: RunRequest) -> RunResult:  # pragma: no cover - protocol
        ...
