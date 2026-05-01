"""Service-layer orchestration tests."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import pytest

from swarmlord.core.errors import GateFailure, SwarmLordError
from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage
from swarmlord.packets.reader import load_packet, load_status
from swarmlord.packets.writer import write_text_atomic
from swarmlord.runners.manual import ManualRunner
from swarmlord.runners.registry import RunnerRegistry
from swarmlord.service import (
    NewPacketSpec,
    dispatch_run,
    extract_packet,
    is_dispatchable,
    list_packets,
    new_packet,
    pick_next,
    promote,
    render_for_packet,
    resolve_packet,
)
from tests.conftest import make_packet


def test_new_packet_creates_layout(repo_root: Path) -> None:
    target = new_packet(
        NewPacketSpec(
            slug="hello-world",
            title="Hello World",
            summary="say hi",
            repo_root=repo_root,
            today=date(2026, 5, 15),
        )
    )
    assert target.exists()
    assert (target / "workflow" / "status.yaml").is_file()
    assert (target / "spec" / "idea.md").is_file()
    s = load_status(target)
    assert s.slug == "2026-05-hello-world"
    assert s.stage is Stage.IDEA
    # Index updated.
    index = (repo_root / "projects" / "INDEX.md").read_text()
    assert "2026-05-hello-world" in index


def test_new_packet_rejects_existing(repo_root: Path) -> None:
    spec = NewPacketSpec(
        slug="dupe",
        title="t",
        summary="",
        repo_root=repo_root,
        today=date(2026, 5, 15),
    )
    new_packet(spec)
    with pytest.raises(SwarmLordError):
        new_packet(spec)


def test_list_and_filter(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-a", stage=Stage.IDEA, phase=Phase.IDEA)
    make_packet(repo_root, slug="2026-05-b", stage=Stage.DISCOVERY, phase=Phase.DISCOVERY)
    all_ = list_packets(repo_root)
    assert len(all_) == 2
    discovery = list_packets(repo_root, stage=Stage.DISCOVERY)
    assert len(discovery) == 1
    assert discovery[0].status.slug == "2026-05-b"


def test_pick_next_orders_by_stage_then_age(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-old", stage=Stage.SPEC_READY)
    make_packet(repo_root, slug="2026-05-new", stage=Stage.IDEA)
    nxt = pick_next(repo_root)
    assert nxt is not None
    assert nxt.status.slug == "2026-05-new"  # earlier stage wins


def test_is_dispatchable_excludes_archived(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-05-arch", stage=Stage.ARCHIVED)
    packets = list_packets(repo_root)
    assert all(not is_dispatchable(p) for p in packets)


def test_promote_with_passing_gates(repo_root: Path) -> None:
    root = make_packet(repo_root, stage=Stage.DISCOVERY)
    write_text_atomic(
        root / "spec" / "discovery.md",
        "# Discovery\n\n## Recommended Direction\n\nGo this way.\n",
    )
    bundle = load_packet(root)
    result = promote(repo_root, bundle, on_disk_today=date(2026, 5, 2))
    assert result.from_stage is Stage.DISCOVERY
    assert result.to_stage is Stage.SPEC_READY
    again = load_status(root)
    assert again.stage is Stage.SPEC_READY


def test_promote_failing_gate_raises(repo_root: Path) -> None:
    root = make_packet(repo_root, stage=Stage.DISCOVERY)
    bundle = load_packet(root)
    with pytest.raises(GateFailure):
        promote(repo_root, bundle)


def test_promote_demote_requires_reason(repo_root: Path) -> None:
    root = make_packet(repo_root, stage=Stage.DISCOVERY)
    bundle = load_packet(root)
    with pytest.raises(SwarmLordError):
        promote(repo_root, bundle, to=Stage.IDEA, demote=True)
    promote(repo_root, bundle, to=Stage.IDEA, demote=True, reason="needs more thinking")
    assert load_status(root).stage is Stage.IDEA


def test_render_for_packet_fallback(repo_root: Path) -> None:
    root = make_packet(repo_root)
    bundle = load_packet(root)
    text = render_for_packet(repo_root, bundle)
    assert "do the thing" in text


def test_render_for_packet_uses_workflow(repo_root: Path) -> None:
    workflow = """---
runner_profile: manual
phase: discovery
---
Slug is {{ packet.slug }}, attempt {{ attempt }}.
"""
    root = make_packet(repo_root, workflow_md=workflow)
    bundle = load_packet(root)
    text = render_for_packet(repo_root, bundle, attempt=2)
    assert "Slug is 2026-05-sample, attempt 2." in text


def test_dispatch_run_with_manual(repo_root: Path) -> None:
    root = make_packet(repo_root)
    bundle = load_packet(root)
    captured: list[str] = []
    registry = RunnerRegistry(
        [
            ManualRunner(
                clipboard=True, clipboard_writer=captured.append, stdout_writer=lambda _: None
            )
        ]
    )
    result, record = asyncio.run(
        dispatch_run(repo_root, bundle, runner_profile="manual", registry=registry)
    )
    assert result.exit_code == 0
    assert record.status == "succeeded"
    assert captured  # manual runner ran with clipboard writer
    # phase_status updated for the rendered phase.
    after = load_status(root)
    assert after.phase_status[Phase.IDEA] == "complete"


def test_extract_packet_requires_build_ready(repo_root: Path) -> None:
    """Extraction without --force only succeeds from build_ready."""
    from swarmlord.core.errors import IllegalTransition

    # Default fixture is at IDEA -> the stage gate must reject.
    root = make_packet(repo_root)
    bundle = load_packet(root)
    target = repo_root / "out"
    with pytest.raises(IllegalTransition):
        extract_packet(repo_root, bundle, target=target, init_git=False)


def test_extract_packet_force_bypasses_gates(repo_root: Path) -> None:
    """force=True skips both stage and predicate gates."""
    root = make_packet(repo_root)
    bundle = load_packet(root)
    target = repo_root / "out"
    result = extract_packet(repo_root, bundle, target=target, init_git=False, force=True)
    assert result.target == target
    assert (target / "README.md").is_file()
    assert (target / "spec" / "idea.md").is_file()
    assert load_status(root).stage is Stage.EXTRACTED


def test_extract_packet_from_build_ready_passes(repo_root: Path) -> None:
    """A packet at build_ready with EXTRACT.md fully resolved extracts cleanly."""
    root = make_packet(repo_root, stage=Stage.BUILD_READY)
    bundle = load_packet(root)
    target = repo_root / "out2"
    result = extract_packet(repo_root, bundle, target=target, init_git=False)
    assert result.target == target
    assert load_status(root).stage is Stage.EXTRACTED


def test_extract_packet_failing_extract_md_raises_gate(repo_root: Path) -> None:
    """A packet at build_ready with unresolved EXTRACT.md must fail the gate."""
    root = make_packet(repo_root, stage=Stage.BUILD_READY)
    write_text_atomic(
        root / "EXTRACT.md",
        "# Extraction\n\n- [ ] still open\n",
    )
    bundle = load_packet(root)
    with pytest.raises(GateFailure):
        extract_packet(repo_root, bundle, target=repo_root / "out3", init_git=False)


def test_resolve_packet_missing(repo_root: Path) -> None:
    with pytest.raises(SwarmLordError):
        resolve_packet(repo_root, "nope")


def test_promote_empty_workflow_gate_list_is_authoritative(repo_root: Path) -> None:
    """If WORKFLOW.md declares an empty gate list, that means "no gates" — not "use defaults"."""
    from swarmlord.service import promote
    from tests.conftest import make_packet

    workflow = """---
runner_profile: manual
phase: discovery
gates:
  promote_to_spec_ready: []
---
empty gates intentionally
"""
    root = make_packet(repo_root, stage=Stage.DISCOVERY, workflow_md=workflow)
    bundle = load_packet(root)
    # Default gates would fail (no Recommended Direction section). Empty
    # list must be honored: promotion succeeds with no gates evaluated.
    result = promote(repo_root, bundle, on_disk_today=date(2026, 5, 2))
    assert result.to_stage is Stage.SPEC_READY
    assert result.gate_results == []


def test_new_packet_already_date_prefixed_slug(repo_root: Path) -> None:
    from swarmlord.service import NewPacketSpec, new_packet

    target = new_packet(
        NewPacketSpec(
            slug="2026-04-already-prefixed",
            title="Already Prefixed",
            summary="",
            repo_root=repo_root,
            today=date(2026, 5, 1),
        )
    )
    assert target.name == "2026-04-already-prefixed"


def test_new_packet_unprefixed_slug_gets_today_prefix(repo_root: Path) -> None:
    from swarmlord.service import NewPacketSpec, new_packet

    target = new_packet(
        NewPacketSpec(
            slug="needs-prefix",
            title="Needs Prefix",
            summary="",
            repo_root=repo_root,
            today=date(2026, 5, 1),
        )
    )
    assert target.name == "2026-05-needs-prefix"


def test_new_packet_slug_starting_with_digits_but_not_date_gets_prefix(
    repo_root: Path,
) -> None:
    """A slug like '12-1234-foo' should still get a date prefix — it isn't a YYYY-MM."""
    from swarmlord.service import NewPacketSpec, new_packet

    target = new_packet(
        NewPacketSpec(
            slug="12-1234-suspicious",
            title="Suspicious",
            summary="",
            repo_root=repo_root,
            today=date(2026, 5, 1),
        )
    )
    assert target.name == "2026-05-12-1234-suspicious"


def test_resolve_runner_profile_precedence(repo_root: Path) -> None:
    from swarmlord.service import resolve_runner_profile
    from tests.conftest import make_packet

    workflow = """---
runner_profile: workflow-profile
phase: discovery
---
"""
    root = make_packet(
        repo_root,
        runner_profile="status-profile",
        workflow_md=workflow,
    )
    bundle = load_packet(root)
    # explicit override wins
    assert resolve_runner_profile(bundle, override="cli-profile") == "cli-profile"
    # then status.runner_profile
    assert resolve_runner_profile(bundle) == "status-profile"


def test_resolve_phase_uses_workflow_then_status_then_stage_default(repo_root: Path) -> None:
    from swarmlord.service import resolve_phase
    from tests.conftest import make_packet

    # No workflow — falls back to status.current_phase.
    root = make_packet(repo_root, stage=Stage.SPEC_READY, phase=Phase.BUILD_SPEC)
    bundle = load_packet(root)
    assert resolve_phase(bundle) is Phase.BUILD_SPEC

    # Workflow phase wins over status.
    workflow = """---
runner_profile: manual
phase: extraction
---
"""
    root2 = make_packet(
        repo_root,
        slug="2026-05-w",
        stage=Stage.SPEC_READY,
        phase=Phase.BUILD_SPEC,
        workflow_md=workflow,
    )
    bundle2 = load_packet(root2)
    assert resolve_phase(bundle2) is Phase.EXTRACTION


def test_dispatch_run_persists_failed_record(repo_root: Path, tmp_path: Path) -> None:
    """A runner that raises must still leave an audit row in SQLite."""

    from swarmlord.runners.base import RunRequest, RunResult
    from swarmlord.runners.registry import RunnerRegistry
    from swarmlord.storage.run_history import RunHistory

    class CrashingRunner:
        name = "manual"

        def can_handle(self, profile: str) -> bool:
            return profile == self.name

        async def run(self, request: RunRequest) -> RunResult:
            raise RuntimeError("kaboom")

    history = RunHistory(tmp_path / "runs.db")
    root = make_packet(repo_root)
    bundle = load_packet(root)
    with pytest.raises(RuntimeError):
        asyncio.run(
            dispatch_run(
                repo_root,
                bundle,
                runner_profile="manual",
                registry=RunnerRegistry([CrashingRunner()]),
                history=history,
            )
        )
    rows = history.list_runs(bundle.status.slug)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["error"] == "kaboom"


def test_dispatch_run_records_commits(repo_root: Path, tmp_path: Path) -> None:
    """Commits returned by the runner must end up on the persisted record."""
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    from swarmlord.runners.base import RunRequest, RunResult
    from swarmlord.runners.registry import RunnerRegistry
    from swarmlord.storage.run_history import RunHistory

    class CommittingRunner:
        name = "manual"

        def can_handle(self, profile: str) -> bool:
            return profile == self.name

        async def run(self, request: RunRequest) -> RunResult:
            now = _dt.now(_UTC)
            return RunResult(
                runner=self.name,
                started_at=now,
                ended_at=now,
                exit_code=0,
                completion_signal_seen="<promise>COMPLETE</promise>",
                commits=["abc1234", "def5678"],
            )

    history = RunHistory(tmp_path / "runs.db")
    root = make_packet(repo_root)
    bundle = load_packet(root)
    _result, record = asyncio.run(
        dispatch_run(
            repo_root,
            bundle,
            runner_profile="manual",
            registry=RunnerRegistry([CommittingRunner()]),
            history=history,
        )
    )
    assert record.commits == ["abc1234", "def5678"]
    rows = history.list_runs(bundle.status.slug)
    assert len(rows) == 1
    assert rows[0]["status"] == "succeeded"
