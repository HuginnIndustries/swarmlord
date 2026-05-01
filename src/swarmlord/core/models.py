"""Pydantic v2 schemas for SwarmLord domain objects.

These models are the typed contract between disk (YAML / Markdown front
matter) and the orchestrator. They never touch the filesystem directly —
that lives in :mod:`swarmlord.packets`.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage

PhaseStatusValue = Literal["pending", "in_progress", "complete", "skipped"]


class _StrictModel(BaseModel):
    """Base for every domain model — extras forbidden, assignments validated."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )


class MemoryStatus(_StrictModel):
    """State recorded by ``swarmlord graphify`` runs."""

    graph_path: str
    report_path: str
    generated_at: datetime


class PacketStatus(_StrictModel):
    """In-memory representation of ``workflow/status.yaml``.

    The packet *root* (the directory holding ``workflow/``) is not stored on
    the model — callers carry it explicitly. That keeps ``status.yaml``
    location-independent for tests and round-trips.
    """

    project_name: str
    slug: str
    stage: Stage
    current_phase: Phase
    created: date
    updated: date
    summary: str = ""
    next_actions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    resolved_questions: list[str] = Field(default_factory=list)
    phase_status: dict[Phase, PhaseStatusValue] = Field(default_factory=dict)
    owner_notes: list[str] = Field(default_factory=list)
    runner_profile: str | None = None
    memory: MemoryStatus | None = None

    @field_validator("phase_status", mode="before")
    @classmethod
    def _coerce_phase_status_keys(cls, value: Any) -> Any:
        """Allow phase_status keys to come in as plain strings from YAML."""
        if not isinstance(value, dict):
            return value
        out: dict[Phase, PhaseStatusValue] = {}
        for k, v in value.items():
            phase = k if isinstance(k, Phase) else Phase(k)
            out[phase] = v
        return out


# --- Predicate vocabulary -------------------------------------------------


class FileExists(_StrictModel):
    kind: Literal["file_exists"]
    path: str


class FileSectionFilled(_StrictModel):
    kind: Literal["file_section_filled"]
    path: str
    section: str
    forbidden_tokens: list[str] = Field(default_factory=lambda: ["TBD", "TODO", "FIXME"])


class YamlFieldEmpty(_StrictModel):
    kind: Literal["yaml_field_empty"]
    path: str
    field: str


class YamlFieldEquals(_StrictModel):
    kind: Literal["yaml_field_equals"]
    path: str
    field: str
    value: str | int | bool


class ExtractMdResolved(_StrictModel):
    kind: Literal["extract_md_resolved"]


class TestsPassing(_StrictModel):
    kind: Literal["tests_passing"]
    command: str


Predicate = Annotated[
    FileExists
    | FileSectionFilled
    | YamlFieldEmpty
    | YamlFieldEquals
    | ExtractMdResolved
    | TestsPassing,
    Field(discriminator="kind"),
]


# --- WorkflowDefinition (parsed from workflow/WORKFLOW.md) ---------------


class WorkflowHooks(_StrictModel):
    after_create: str | None = None
    before_run: str | None = None
    after_run: str | None = None
    before_remove: str | None = None
    timeout_ms: int = 60_000


class AgentConfig(_StrictModel):
    max_turns: int = 20
    stall_timeout_ms: int = 300_000
    max_retry_backoff_ms: int = 300_000
    completion_signal: str | list[str] = "<promise>COMPLETE</promise>"
    idle_timeout_seconds: int = 600


class GateConfig(_StrictModel):
    promote_to_spec_ready: list[Predicate] = Field(default_factory=list)
    promote_to_build_ready: list[Predicate] = Field(default_factory=list)
    promote_to_extracted: list[Predicate] = Field(default_factory=list)


class WorkflowDefinition(_StrictModel):
    runner_profile: str
    phase: Phase
    hooks: WorkflowHooks = Field(default_factory=WorkflowHooks)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    gates: GateConfig = Field(default_factory=GateConfig)
    prompt_template: str  # populated from the body of WORKFLOW.md


# --- Run record (mirrors SQLite schema + per-packet YAML log) ------------


class RunRecord(_StrictModel):
    """One execution of a runner against a packet phase."""

    id: str  # uuid4 hex
    packet_slug: str
    runner_profile: str
    phase: Phase
    attempt: int
    prompt_hash: str
    started_at: datetime
    ended_at: datetime | None = None
    exit_code: int | None = None
    completion_signal_seen: str | None = None
    log_path: Path | None = None
    transcript_path: Path | None = None
    commits: list[str] = Field(default_factory=list)
    transitions_triggered: list[str] = Field(default_factory=list)
    error: str | None = None
    status: Literal["running", "succeeded", "failed", "aborted"] = "running"
