"""Typed exceptions raised across the swarmlord library.

All library errors derive from :class:`SwarmLordError` so the CLI can render a
single human-friendly handler instead of dumping a Python traceback.
"""

from __future__ import annotations


class SwarmLordError(Exception):
    """Base for every domain-level error raised by swarmlord."""


class PacketSchemaError(SwarmLordError):
    """Raised when a packet's ``status.yaml`` fails Pydantic validation."""


class WorkflowParseError(SwarmLordError):
    """Raised when ``workflow/WORKFLOW.md`` cannot be parsed."""


class IllegalTransition(SwarmLordError):  # noqa: N818 - domain-specific name from spec
    """Raised when a stage transition is not allowed by the state machine."""

    def __init__(self, from_stage: str, to_stage: str) -> None:
        super().__init__(f"Illegal stage transition: {from_stage} -> {to_stage}")
        self.from_stage = from_stage
        self.to_stage = to_stage


class GateFailure(SwarmLordError):  # noqa: N818 - domain-specific name from spec
    """Raised when one or more gate predicates fail during a promotion attempt."""

    def __init__(self, failures: list[str]) -> None:
        super().__init__("Gate predicates failed:\n  - " + "\n  - ".join(failures))
        self.failures = failures


class TemplateRenderError(SwarmLordError):
    """Raised when Jinja2 template rendering fails (typically StrictUndefined)."""


class RunnerError(SwarmLordError):
    """Raised when a runner subprocess fails or returns malformed output."""


class PacketWriteError(SwarmLordError):
    """Raised when an atomic packet write cannot complete."""
