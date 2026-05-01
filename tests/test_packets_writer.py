"""Atomic writer tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from swarmlord.core.errors import PacketWriteError
from swarmlord.packets.reader import load_status
from swarmlord.packets.thread_log import append_thread_log
from swarmlord.packets.writer import write_status, write_text_atomic


def test_write_text_atomic_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c.txt"
    write_text_atomic(target, "hello\n")
    assert target.read_text() == "hello\n"


def test_write_text_atomic_replaces(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    write_text_atomic(target, "first")
    write_text_atomic(target, "second")
    assert target.read_text() == "second"


def test_write_status_round_trips(sample_packet: Path) -> None:
    s = load_status(sample_packet)
    write_status(sample_packet, s)
    again = load_status(sample_packet)
    assert again.slug == s.slug
    assert again.stage == s.stage


def test_atomic_write_failure_leaves_disk_parseable(sample_packet: Path) -> None:
    """If os.replace fails mid-write, the on-disk packet must still parse.

    The original ``status.yaml`` is untouched until ``os.replace`` completes,
    so a failure leaves the *previous* status on disk intact.
    """
    original = load_status(sample_packet)
    new = original.model_copy(update={"summary": "MUTATED"})
    with (
        patch("swarmlord.packets.writer.os.replace", side_effect=OSError("boom")),
        pytest.raises(PacketWriteError),
    ):
        write_status(sample_packet, new)
    after = load_status(sample_packet)
    assert after.summary == original.summary
    # No leftover temp files in the workflow dir.
    leftovers = [p for p in (sample_packet / "workflow").iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_thread_log_appends(sample_packet: Path) -> None:
    log = sample_packet / "THREAD_LOG.md"
    if log.exists():
        os.remove(log)
    append_thread_log(sample_packet, "first")
    append_thread_log(sample_packet, "second")
    text = log.read_text(encoding="utf-8")
    assert "first" in text
    assert "second" in text
    # Both bullets present in the log.
    assert "first" in text and "second" in text
