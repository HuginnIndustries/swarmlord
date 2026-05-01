"""Stage transition table tests."""

from __future__ import annotations

import pytest

from swarmlord.core.errors import IllegalTransition
from swarmlord.core.stages import Stage, assert_transition, can_transition, is_forward, next_stage


def test_legal_forward_transitions() -> None:
    assert can_transition(Stage.IDEA, Stage.DISCOVERY)
    assert can_transition(Stage.DISCOVERY, Stage.SPEC_READY)
    assert can_transition(Stage.SPEC_READY, Stage.BUILD_READY)
    assert can_transition(Stage.BUILD_READY, Stage.EXTRACTED)


def test_legal_backward_transitions() -> None:
    assert can_transition(Stage.DISCOVERY, Stage.IDEA)
    assert can_transition(Stage.SPEC_READY, Stage.DISCOVERY)
    assert can_transition(Stage.BUILD_READY, Stage.SPEC_READY)


def test_archive_is_terminal() -> None:
    assert not can_transition(Stage.ARCHIVED, Stage.IDEA)
    assert not can_transition(Stage.EXTRACTED, Stage.BUILD_READY)


def test_illegal_transition_raises() -> None:
    with pytest.raises(IllegalTransition):
        assert_transition(Stage.IDEA, Stage.BUILD_READY)


def test_next_stage_walks_forward() -> None:
    assert next_stage(Stage.IDEA) is Stage.DISCOVERY
    assert next_stage(Stage.SPEC_READY) is Stage.BUILD_READY
    assert next_stage(Stage.EXTRACTED) is None
    assert next_stage(Stage.ARCHIVED) is None


def test_is_forward_excludes_archive() -> None:
    assert is_forward(Stage.IDEA, Stage.SPEC_READY)
    assert not is_forward(Stage.SPEC_READY, Stage.IDEA)
    # Archive transitions are not "forward" in the gated sense:
    assert not is_forward(Stage.IDEA, Stage.ARCHIVED)
