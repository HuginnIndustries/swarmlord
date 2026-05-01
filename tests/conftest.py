"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from swarmlord.core.models import PacketStatus
from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage
from swarmlord.packets.writer import write_status, write_text_atomic


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    (tmp_path / "projects").mkdir()
    return tmp_path


def make_packet(
    repo_root: Path,
    *,
    slug: str = "2026-05-sample",
    stage: Stage = Stage.IDEA,
    phase: Phase = Phase.IDEA,
    summary: str = "sample packet",
    next_actions: list[str] | None = None,
    open_questions: list[str] | None = None,
    runner_profile: str | None = None,
    workflow_md: str | None = None,
) -> Path:
    """Create a packet on disk and return its root path."""
    root = repo_root / "projects" / slug
    (root / "workflow").mkdir(parents=True)
    (root / "spec").mkdir(parents=True)
    status = PacketStatus(
        project_name=slug,
        slug=slug,
        stage=stage,
        current_phase=phase,
        created=date(2026, 5, 1),
        updated=date(2026, 5, 1),
        summary=summary,
        next_actions=next_actions or ["do the thing"],
        open_questions=open_questions or [],
        phase_status={
            Phase.IDEA: "pending",
            Phase.DISCOVERY: "pending",
            Phase.BUILD_SPEC: "pending",
            Phase.EXTRACTION: "pending",
        },
        runner_profile=runner_profile,
    )
    write_status(root, status)
    if workflow_md is not None:
        write_text_atomic(root / "workflow" / "WORKFLOW.md", workflow_md)
    write_text_atomic(root / "README.md", f"# {slug}\n")
    write_text_atomic(root / "EXTRACT.md", "# Extraction Checklist\n\n- [x] something done\n")
    write_text_atomic(root / "spec" / "idea.md", "# Idea\n")
    write_text_atomic(root / "spec" / "discovery.md", "# Discovery\n")
    write_text_atomic(root / "spec" / "build-spec.md", "# Build Spec\n")
    return root


@pytest.fixture
def sample_packet(repo_root: Path) -> Path:
    return make_packet(repo_root)
