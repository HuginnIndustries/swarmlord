"""Reader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarmlord.core.errors import PacketSchemaError
from swarmlord.core.stages import Stage
from swarmlord.packets.reader import dump_status_yaml, load_packet, load_status


def test_load_status_returns_typed(sample_packet: Path) -> None:
    s = load_status(sample_packet)
    assert s.stage is Stage.IDEA
    assert s.slug == "2026-05-sample"


def test_load_status_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_status(tmp_path)


def test_load_status_bad_schema(tmp_path: Path) -> None:
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "status.yaml").write_text("project_name: only-this", encoding="utf-8")
    with pytest.raises(PacketSchemaError):
        load_status(tmp_path)


def test_dump_round_trips(sample_packet: Path) -> None:
    s = load_status(sample_packet)
    raw = dump_status_yaml(s)
    assert "stage: idea" in raw
    assert "slug: 2026-05-sample" in raw


def test_load_packet_optional_workflow(sample_packet: Path) -> None:
    bundle = load_packet(sample_packet)
    assert bundle.status.slug == "2026-05-sample"
    assert bundle.workflow is None
