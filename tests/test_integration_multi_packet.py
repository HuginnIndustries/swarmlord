"""Multi-packet listing and ordering."""

from __future__ import annotations

from pathlib import Path

from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage
from swarmlord.service import list_packets, pick_next
from tests.conftest import make_packet


def test_three_packets_pick_correct_next(repo_root: Path) -> None:
    make_packet(repo_root, slug="2026-04-archived", stage=Stage.ARCHIVED, phase=Phase.IDEA)
    make_packet(repo_root, slug="2026-05-discovery", stage=Stage.DISCOVERY, phase=Phase.DISCOVERY)
    make_packet(repo_root, slug="2026-05-idea", stage=Stage.IDEA, phase=Phase.IDEA)
    all_packets = list_packets(repo_root)
    assert len(all_packets) == 3
    nxt = pick_next(repo_root)
    assert nxt is not None
    assert nxt.status.slug == "2026-05-idea"
