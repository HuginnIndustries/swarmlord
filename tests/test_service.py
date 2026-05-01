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


def test_extract_packet(repo_root: Path) -> None:
    root = make_packet(repo_root)
    bundle = load_packet(root)
    target = repo_root / "out"
    result = extract_packet(repo_root, bundle, target=target, init_git=False)
    assert result.target == target
    assert (target / "README.md").is_file()
    assert (target / "spec" / "idea.md").is_file()
    assert load_status(root).stage is Stage.EXTRACTED


def test_resolve_packet_missing(repo_root: Path) -> None:
    with pytest.raises(SwarmLordError):
        resolve_packet(repo_root, "nope")
