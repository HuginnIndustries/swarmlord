"""High-level orchestration glue used by the CLI.

The service module composes :mod:`swarmlord.core`, :mod:`swarmlord.packets`,
:mod:`swarmlord.templating`, and :mod:`swarmlord.runners` into the operations
the user invokes (``new``, ``next``, ``promote``, ``render``, ``extract`` …).
The CLI is a thin Typer wrapper around what's here.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib import resources
from pathlib import Path

from swarmlord.core.errors import (
    GateFailure,
    SwarmLordError,
)
from swarmlord.core.gates import GateResult, evaluate_gate
from swarmlord.core.models import (
    AgentConfig,
    ExtractMdResolved,
    FileSectionFilled,
    GateConfig,
    PacketStatus,
    Predicate,
    RunRecord,
    WorkflowDefinition,
    WorkflowHooks,
    YamlFieldEmpty,
)
from swarmlord.core.phases import Phase
from swarmlord.core.stages import (
    FORWARD_ORDER,
    Stage,
    assert_transition,
    is_forward,
    next_stage,
)
from swarmlord.packets.discovery import (
    DiscoveredPacket,
    discover_packets,
    find_packet,
)
from swarmlord.packets.index import IndexEntry, upsert_index_entry
from swarmlord.packets.reader import PacketBundle, load_packet
from swarmlord.packets.thread_log import append_thread_log
from swarmlord.packets.writer import write_status
from swarmlord.runners.base import RunRequest, RunResult
from swarmlord.runners.registry import RunnerRegistry, default_registry
from swarmlord.storage.run_history import RunHistory
from swarmlord.templating.engine import render_prompt

# A best-effort mapping from stage to the phase that fits work in that stage.
# Used as a *fallback* when neither WORKFLOW.md nor status.current_phase tells
# us what to render. This lets a packet with a stale current_phase still get
# a sensible prompt rendered.
PHASE_FOR_STAGE: dict[Stage, Phase] = {
    Stage.IDEA: Phase.IDEA,
    Stage.DISCOVERY: Phase.DISCOVERY,
    Stage.SPEC_READY: Phase.BUILD_SPEC,
    Stage.BUILD_READY: Phase.EXTRACTION,
    Stage.EXTRACTED: Phase.EXTRACTION,
    Stage.ARCHIVED: Phase.EXTRACTION,
}

# Slug shape: a date prefix is "YYYY-MM-" followed by a non-empty body.
_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-")


# --- Defaults --------------------------------------------------------------


def default_gate_config() -> GateConfig:
    """Built-in gates used when a packet has no ``WORKFLOW.md`` at all."""
    return GateConfig(
        promote_to_spec_ready=[
            FileSectionFilled(
                kind="file_section_filled",
                path="spec/discovery.md",
                section="## Recommended Direction",
            ),
            YamlFieldEmpty(
                kind="yaml_field_empty",
                path="workflow/status.yaml",
                field="open_questions",
            ),
        ],
        promote_to_build_ready=[
            FileSectionFilled(
                kind="file_section_filled",
                path="spec/build-spec.md",
                section="## Outcome",
            ),
            FileSectionFilled(
                kind="file_section_filled",
                path="spec/build-spec.md",
                section="## Acceptance Criteria",
            ),
            FileSectionFilled(
                kind="file_section_filled",
                path="spec/build-spec.md",
                section="## Test Plan",
            ),
            YamlFieldEmpty(
                kind="yaml_field_empty",
                path="workflow/status.yaml",
                field="open_questions",
            ),
            ExtractMdResolved(kind="extract_md_resolved"),
        ],
        promote_to_extracted=[
            ExtractMdResolved(kind="extract_md_resolved"),
        ],
    )


def default_workflow_definition(
    *,
    runner_profile: str = "manual",
    phase: Phase = Phase.DISCOVERY,
    prompt_template: str = "",
) -> WorkflowDefinition:
    """The single source of truth for a ``WorkflowDefinition`` when no
    ``WORKFLOW.md`` exists on disk. Combines :func:`default_gate_config`
    with default hooks and agent config.
    """
    return WorkflowDefinition(
        runner_profile=runner_profile,
        phase=phase,
        hooks=WorkflowHooks(),
        agent=AgentConfig(),
        gates=default_gate_config(),
        prompt_template=prompt_template,
    )


def gate_predicates_for(target_stage: Stage, gates: GateConfig) -> list[Predicate]:
    if target_stage is Stage.SPEC_READY:
        return list(gates.promote_to_spec_ready)
    if target_stage is Stage.BUILD_READY:
        return list(gates.promote_to_build_ready)
    if target_stage is Stage.EXTRACTED:
        return list(gates.promote_to_extracted)
    return []


# --- Listing & dispatchability --------------------------------------------


def list_packets(
    repo_root: Path,
    *,
    stage: Stage | None = None,
    phase: Phase | None = None,
) -> list[DiscoveredPacket]:
    packets = discover_packets(repo_root)
    if stage is not None:
        packets = [p for p in packets if p.status.stage is stage]
    if phase is not None:
        packets = [p for p in packets if p.status.current_phase is phase]
    return packets


def is_dispatchable(packet: DiscoveredPacket) -> bool:
    """A packet is dispatchable if it isn't terminal and has next actions.

    EXTRACTED and ARCHIVED are both treated as terminal: an extracted packet
    has moved its work to a separate repo, so the source packet shouldn't
    show up in ``swarmlord next`` (the extracted repo is where work continues).
    """
    if packet.status.stage in (Stage.ARCHIVED, Stage.EXTRACTED):
        return False
    return bool(packet.status.next_actions)


def pick_next(
    repo_root: Path,
    *,
    stage: Stage | None = None,
    runner_profile: str | None = None,
) -> DiscoveredPacket | None:
    candidates = [p for p in list_packets(repo_root, stage=stage) if is_dispatchable(p)]
    if runner_profile is not None:
        candidates = [p for p in candidates if (p.status.runner_profile or "") == runner_profile]
    if not candidates:
        return None
    candidates.sort(key=lambda p: (FORWARD_ORDER.index(p.status.stage), p.status.updated))
    return candidates[0]


# --- New packet scaffolding -----------------------------------------------


@dataclass(slots=True, frozen=True)
class NewPacketSpec:
    slug: str
    title: str
    summary: str
    repo_root: Path
    today: date
    runner_profile: str | None = None


def template_root(repo_root: Path) -> Path:
    """Resolve where the packet template lives.

    Order: repo-local ``templates/packet/`` first (per spec); otherwise fall
    back to the bundled template that ships inside the wheel.
    """
    repo_local = repo_root / "templates" / "packet"
    if repo_local.is_dir():
        return repo_local
    with resources.as_file(resources.files("swarmlord") / "_templates" / "packet") as p:
        return Path(p)


def _is_date_prefixed(slug: str) -> bool:
    """Return True if ``slug`` already starts with ``YYYY-MM-``."""
    return _DATE_PREFIX_RE.match(slug) is not None


def new_packet(spec: NewPacketSpec) -> Path:
    """Scaffold a new packet under ``projects/<YYYY-MM-slug>/``.

    Returns the new packet's root path. Raises if the directory already
    exists. Adds an INDEX entry on success.
    """
    folder_slug = (
        spec.slug if _is_date_prefixed(spec.slug) else f"{spec.today.strftime('%Y-%m')}-{spec.slug}"
    )
    target = spec.repo_root / "projects" / folder_slug
    if target.exists():
        raise SwarmLordError(f"packet directory already exists: {target}")
    src_root = template_root(spec.repo_root)
    shutil.copytree(src_root, target)
    # Materialize a real status.yaml from the template values.
    status = PacketStatus(
        project_name=spec.title or spec.slug,
        slug=folder_slug,
        stage=Stage.IDEA,
        current_phase=Phase.IDEA,
        created=spec.today,
        updated=spec.today,
        summary=spec.summary,
        next_actions=["Capture the raw idea in spec/idea.md."],
        phase_status={
            Phase.IDEA: "in_progress",
            Phase.DISCOVERY: "pending",
            Phase.BUILD_SPEC: "pending",
            Phase.EXTRACTION: "pending",
        },
        runner_profile=spec.runner_profile,
    )
    write_status(target, status)
    upsert_index_entry(
        spec.repo_root,
        IndexEntry(slug=folder_slug, stage=Stage.IDEA.value, summary=spec.summary or "(new)"),
    )
    append_thread_log(target, f"Packet created via `swarmlord new {spec.slug}`.", when=spec.today)
    return target


# --- Render ---------------------------------------------------------------


def resolve_phase(bundle: PacketBundle, override: Phase | None = None) -> Phase:
    """Resolve which phase to render against.

    Precedence: explicit ``override`` (caller said so) > ``workflow.phase``
    (packet says so via WORKFLOW.md) > ``status.current_phase`` (packet's
    last-known phase pointer) > :data:`PHASE_FOR_STAGE` (sensible default
    derived from the stage when nothing else is set).
    """
    if override is not None:
        return override
    if bundle.workflow is not None:
        return bundle.workflow.phase
    return bundle.status.current_phase


def render_for_packet(
    repo_root: Path,
    bundle: PacketBundle,
    *,
    phase: Phase | None = None,
    attempt: int = 0,
    prior_run_summary: str = "",
) -> str:
    """Render the prompt for ``bundle``'s current (or specified) phase."""
    workflow = bundle.workflow
    target_phase = resolve_phase(bundle, override=phase)
    if workflow is None:
        return _fallback_prompt(bundle.status, target_phase, repo_root, bundle.root)
    graph_report = bundle.status.memory.report_path if bundle.status.memory else None
    return render_prompt(
        workflow.prompt_template,
        bundle.status,
        repo_root=repo_root,
        packet_root=bundle.root,
        attempt=attempt,
        prior_run_summary=prior_run_summary,
        graph_report_path=graph_report,
    )


def _fallback_prompt(
    status: PacketStatus,
    phase: Phase,
    repo_root: Path,
    packet_root: Path,
) -> str:
    nx = "\n".join(f"- {a}" for a in status.next_actions) or "- (none specified)"
    oq = "\n".join(f"- {q}" for q in status.open_questions) or "- (none open)"
    return (
        f"Packet: {status.slug}\n"
        f"Stage: {status.stage.value}\n"
        f"Phase: {phase.value}\n"
        f"Repo root: {repo_root}\n"
        f"Packet root: {packet_root}\n\n"
        f"Next actions:\n{nx}\n\n"
        f"Open questions:\n{oq}\n"
    )


# --- Promotion ------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class PromotionResult:
    from_stage: Stage
    to_stage: Stage
    gate_results: list[GateResult]


def promote(
    repo_root: Path,
    bundle: PacketBundle,
    *,
    to: Stage | None = None,
    reason: str | None = None,
    demote: bool = False,
    on_disk_today: date | None = None,
) -> PromotionResult:
    """Run gates and transition the packet's stage.

    Gate semantics:
    * If WORKFLOW.md is present, its ``gates`` are authoritative — including
      the empty-list case (declaring "no gates for this transition" is a
      valid choice).
    * If WORKFLOW.md is absent, the built-in defaults from
      :func:`default_gate_config` apply.

    ``demote=True`` skips gates and requires a ``reason``. The transition is
    written to ``status.yaml``, ``THREAD_LOG.md``, and ``projects/INDEX.md``
    in that order; the on-disk packet is consistent at every step.
    """
    from_stage = bundle.status.stage
    target = to or next_stage(from_stage)
    if target is None:
        raise SwarmLordError(f"no forward stage available from {from_stage.value}")
    assert_transition(from_stage, target)

    gates_to_run: list[Predicate] = []
    if not demote and is_forward(from_stage, target):
        # WORKFLOW.md present → it is authoritative (including empty lists).
        # WORKFLOW.md absent → fall back to defaults.
        gates = bundle.workflow.gates if bundle.workflow else default_gate_config()
        gates_to_run = gate_predicates_for(target, gates)

    results = evaluate_gate(gates_to_run, bundle.root) if gates_to_run else []
    failures = [r for r in results if not r.passed]
    if failures and not demote:
        raise GateFailure([r.message for r in failures])

    if demote and not reason:
        raise SwarmLordError("demotion requires a --reason")

    today = on_disk_today or date.today()
    new_status = bundle.status.model_copy(update={"stage": target, "updated": today})
    write_status(bundle.root, new_status)
    if reason:
        append_thread_log(
            bundle.root,
            f"Stage {from_stage.value} -> {target.value} (reason: {reason}).",
            when=today,
        )
    else:
        append_thread_log(
            bundle.root,
            f"Stage {from_stage.value} -> {target.value} (gates passed).",
            when=today,
        )
    upsert_index_entry(
        repo_root,
        IndexEntry(slug=new_status.slug, stage=target.value, summary=new_status.summary),
    )
    return PromotionResult(from_stage=from_stage, to_stage=target, gate_results=results)


# --- Run dispatch ---------------------------------------------------------


def resolve_runner_profile(
    bundle: PacketBundle,
    override: str | None = None,
    *,
    fallback: str = "manual",
) -> str:
    """Resolve which runner profile to dispatch to.

    Precedence: explicit ``override`` > ``status.runner_profile``
    (per-packet pin) > ``workflow.runner_profile`` (declared in WORKFLOW.md)
    > ``fallback`` (the registry's default-of-last-resort, ``"manual"``).
    """
    if override:
        return override
    if bundle.status.runner_profile:
        return bundle.status.runner_profile
    if bundle.workflow is not None:
        return bundle.workflow.runner_profile
    return fallback


def make_run_record(
    bundle: PacketBundle,
    *,
    runner_profile: str,
    rendered_prompt: str,
    phase: Phase,
    attempt: int = 0,
) -> RunRecord:
    return RunRecord(
        id=uuid.uuid4().hex,
        packet_slug=bundle.status.slug,
        runner_profile=runner_profile,
        phase=phase,
        attempt=attempt,
        prompt_hash=hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest(),
        started_at=datetime.now(UTC),
    )


async def dispatch_run(
    repo_root: Path,
    bundle: PacketBundle,
    *,
    runner_profile: str | None = None,
    registry: RunnerRegistry | None = None,
    attempt: int = 0,
    on_disk_today: date | None = None,
    history: RunHistory | None = None,
) -> tuple[RunResult, RunRecord]:
    """Render + dispatch + record. Updates ``status.phase_status`` on success.

    The run record is persisted to ``history`` (when provided) on *both* the
    success and exception paths, so a runner crash or malformed Sandcastle
    summary still leaves an audit row in SQLite. The exception then re-raises
    to the caller; the caller can find the failed record via
    ``history.list_runs(slug)``.
    """
    profile = resolve_runner_profile(bundle, runner_profile)
    target_phase = resolve_phase(bundle)
    rendered = render_for_packet(repo_root, bundle, phase=target_phase, attempt=attempt)
    runner_registry = registry or default_registry()
    runner = runner_registry.resolve(profile)
    record = make_run_record(
        bundle,
        runner_profile=profile,
        rendered_prompt=rendered,
        phase=target_phase,
        attempt=attempt,
    )
    workflow = bundle.workflow or default_workflow_definition(
        runner_profile=profile,
        phase=target_phase,
    )
    request = RunRequest(
        packet_slug=bundle.status.slug,
        packet_root=bundle.root,
        rendered_prompt=rendered,
        workflow=workflow,
    )
    try:
        result = await runner.run(request)
    except Exception as exc:
        record = record.model_copy(
            update={
                "ended_at": datetime.now(UTC),
                "exit_code": -1,
                "status": "failed",
                "error": str(exc),
            }
        )
        if history is not None:
            history.insert_run(record)
        raise
    today = on_disk_today or date.today()
    record = record.model_copy(
        update={
            "ended_at": result.ended_at,
            "exit_code": result.exit_code,
            "completion_signal_seen": result.completion_signal_seen,
            "log_path": result.log_path,
            "transcript_path": result.transcript_path,
            "commits": list(result.commits),
            "status": "succeeded" if result.exit_code == 0 else "failed",
        }
    )
    if result.exit_code == 0:
        new_phase_status = dict(bundle.status.phase_status)
        new_phase_status[target_phase] = "complete"
        new_status = bundle.status.model_copy(
            update={"phase_status": new_phase_status, "updated": today}
        )
        write_status(bundle.root, new_status)
    if history is not None:
        history.insert_run(record)
    return result, record


# --- Extract --------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ExtractionResult:
    target: Path
    files_copied: int


def extract_packet(
    repo_root: Path,
    bundle: PacketBundle,
    *,
    target: Path,
    init_git: bool = True,
    force: bool = False,
    on_disk_today: date | None = None,
) -> ExtractionResult:
    """Execute the EXTRACT.md flow into a new repo path.

    Defaults require the source packet to be at stage ``build_ready`` and
    the ``promote_to_extracted`` gates (``ExtractMdResolved`` + any
    WORKFLOW.md additions) to pass. Pass ``force=True`` to bypass both
    checks — useful for emergency extraction of a half-finished packet.
    """
    if target.exists():
        raise SwarmLordError(f"extract target already exists: {target}")
    if not force:
        # Stage gate: only build_ready packets are extractable forward.
        # The legal-transition table forbids any other origin.
        assert_transition(bundle.status.stage, Stage.EXTRACTED)
        # Predicate gate: same shape as promote(), so a packet that would
        # fail `swarmlord promote --to extracted` also fails `extract`.
        gates = bundle.workflow.gates if bundle.workflow else default_gate_config()
        predicates = gate_predicates_for(Stage.EXTRACTED, gates)
        results = evaluate_gate(predicates, bundle.root) if predicates else []
        failures = [r for r in results if not r.passed]
        if failures:
            raise GateFailure([r.message for r in failures])
    target.mkdir(parents=True)
    files_copied = 0
    for name in ("README.md", "GUIDE.md", "THREAD_LOG.md", "EXTRACT.md"):
        src = bundle.root / name
        if src.is_file():
            shutil.copy2(src, target / name)
            files_copied += 1
    for dirname in ("spec", "workflow", "skills"):
        src = bundle.root / dirname
        if src.is_dir():
            shutil.copytree(src, target / dirname)
            files_copied += sum(1 for _ in (target / dirname).rglob("*") if _.is_file())
    if init_git:
        # Best-effort — tests do not require git on PATH.
        with contextlib.suppress(FileNotFoundError, subprocess.CalledProcessError):
            subprocess.run(
                ["git", "init", "-q"],
                cwd=target,
                check=True,
                capture_output=True,
            )
    today = on_disk_today or date.today()
    new_status = bundle.status.model_copy(update={"stage": Stage.EXTRACTED, "updated": today})
    write_status(bundle.root, new_status)
    upsert_index_entry(
        repo_root,
        IndexEntry(
            slug=new_status.slug,
            stage=Stage.EXTRACTED.value,
            summary=new_status.summary,
            extracted_to=str(target),
        ),
    )
    append_thread_log(
        bundle.root,
        f"Extracted to {target}.",
        when=today,
    )
    return ExtractionResult(target=target, files_copied=files_copied)


# --- Validation -----------------------------------------------------------


def validate_packet(packet_root: Path) -> PacketBundle:
    """Schema-validate a packet on disk and return its bundle on success."""
    return load_packet(packet_root)


def validate_all(repo_root: Path) -> list[tuple[Path, Exception | None]]:
    """Validate every packet in the repo. Returns (root, error or None)."""
    out: list[tuple[Path, Exception | None]] = []
    for status_file in sorted((repo_root / "projects").glob("*/workflow/status.yaml")):
        root = status_file.parent.parent
        try:
            validate_packet(root)
            out.append((root, None))
        except Exception as exc:
            out.append((root, exc))
    return out


# --- Helpers --------------------------------------------------------------


def resolve_packet(repo_root: Path, slug: str) -> PacketBundle:
    """Find a packet by slug and return its bundle, or raise."""
    found = find_packet(repo_root, slug)
    if found is None:
        raise SwarmLordError(f"no packet found with slug or folder name '{slug}'")
    return load_packet(found.root)
