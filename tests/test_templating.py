"""Templating contract: StrictUndefined, literal user content, custom filters."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from swarmlord.core.errors import TemplateRenderError
from swarmlord.core.models import PacketStatus
from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage
from swarmlord.templating.engine import render_prompt, render_string
from swarmlord.templating.filters import (
    default_empty,
    indent_filter,
    summarize,
    trim_filter,
)


def _packet(open_questions: list[str] | None = None) -> PacketStatus:
    return PacketStatus(
        project_name="p",
        slug="2026-05-p",
        stage=Stage.DISCOVERY,
        current_phase=Phase.DISCOVERY,
        created=date(2026, 5, 1),
        updated=date(2026, 5, 1),
        summary="hi",
        next_actions=["x"],
        open_questions=open_questions or [],
    )


def test_strict_undefined_raises_on_typo(tmp_path: Path) -> None:
    with pytest.raises(TemplateRenderError):
        render_prompt(
            "Hello {{ pakcet.slug }}",  # typo
            _packet(),
            repo_root=tmp_path,
            packet_root=tmp_path,
        )


def test_user_supplied_braces_are_literal(tmp_path: Path) -> None:
    out = render_prompt(
        "Open: {% for q in packet.open_questions %}{{ q }};{% endfor %}",
        _packet(open_questions=["use {{ var }} for substitution"]),
        repo_root=tmp_path,
        packet_root=tmp_path,
    )
    # The dangerous-looking content must survive verbatim — not get re-evaluated.
    assert "{{ var }}" in out


def test_attempt_block(tmp_path: Path) -> None:
    out = render_prompt(
        "{% if attempt %}retry {{ attempt }}{% endif %}",
        _packet(),
        repo_root=tmp_path,
        packet_root=tmp_path,
        attempt=3,
    )
    assert "retry 3" in out


def test_custom_filters() -> None:
    assert trim_filter("  hi  ") == "hi"
    assert trim_filter(None) == ""
    assert indent_filter("a\n\nb", 2) == "  a\n\n  b"
    assert default_empty(None, "fallback") == "fallback"
    assert default_empty("v") == "v"
    assert summarize("a b c d e", 3) == "a b c..."
    assert summarize("short") == "short"


def test_render_string_uses_filters(tmp_path: Path) -> None:
    out = render_prompt(
        "{{ packet.summary | summarize(1) }}",
        _packet().model_copy(update={"summary": "one two three"}),
        repo_root=tmp_path,
        packet_root=tmp_path,
    )
    assert "one..." in out


def test_render_string_low_level(tmp_path: Path) -> None:
    from swarmlord.templating.engine import build_context

    ctx = build_context(_packet(), repo_root=tmp_path, packet_root=tmp_path)
    assert render_string("{{ packet.slug }}", ctx) == "2026-05-p"


def test_render_is_deterministic_byte_identical(tmp_path: Path) -> None:
    """Acceptance Criterion #4: identical inputs must produce byte-identical output.

    Catches accidental injection of timestamps, random IDs, or anything
    that would silently make rendered prompts non-reproducible.
    """
    template = (
        "packet: {{ packet.slug }}\n"
        "stage: {{ packet.stage.value }}\n"
        "phase: {{ packet.current_phase.value }}\n"
        "next:\n{% for a in packet.next_actions %}- {{ a }}\n{% endfor %}"
        "{% if attempt %}retry {{ attempt }}\n{% endif %}"
    )
    pkt = _packet(open_questions=["does this matter?"]).model_copy(
        update={"next_actions": ["one", "two"]}
    )
    a = render_prompt(template, pkt, repo_root=tmp_path, packet_root=tmp_path, attempt=2)
    b = render_prompt(template, pkt, repo_root=tmp_path, packet_root=tmp_path, attempt=2)
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")
