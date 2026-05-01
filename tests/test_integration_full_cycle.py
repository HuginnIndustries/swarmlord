"""End-to-end: scaffold a packet, render, promote through stages."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from swarmlord.core.stages import Stage
from swarmlord.packets.reader import load_packet, load_status
from swarmlord.packets.writer import write_text_atomic
from swarmlord.service import (
    NewPacketSpec,
    new_packet,
    promote,
    render_for_packet,
)


def test_full_idea_to_spec_ready(repo_root: Path) -> None:
    target = new_packet(
        NewPacketSpec(
            slug="thing",
            title="Thing",
            summary="just a thing",
            repo_root=repo_root,
            today=date(2026, 5, 15),
        )
    )
    bundle = load_packet(target)
    # Render works on a fresh packet (uses bundled WORKFLOW.md template).
    rendered = render_for_packet(repo_root, bundle)
    assert "thing" in rendered

    # Promote idea -> discovery (no gates declared on this transition).
    result = promote(repo_root, bundle, to=Stage.DISCOVERY, on_disk_today=date(2026, 5, 16))
    assert result.to_stage is Stage.DISCOVERY

    # Fill discovery; promote discovery -> spec_ready.
    write_text_atomic(
        target / "spec" / "discovery.md",
        "# Discovery\n\n## Recommended Direction\n\nDo this.\n",
    )
    bundle2 = load_packet(target)
    result2 = promote(repo_root, bundle2, on_disk_today=date(2026, 5, 17))
    assert result2.to_stage is Stage.SPEC_READY

    # THREAD_LOG accumulated entries.
    log = (target / "THREAD_LOG.md").read_text()
    assert log.count("\n- ") >= 2

    # status.yaml stage updated and INDEX reflects it.
    final = load_status(target)
    assert final.stage is Stage.SPEC_READY
    assert "2026-05-thing" in (repo_root / "projects" / "INDEX.md").read_text()
