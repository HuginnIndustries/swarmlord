"""Stage enum and the legal-transition table.

Promotion forward goes through gate evaluation in :mod:`swarmlord.core.gates`.
Demotion backward is always allowed (the CLI requires a ``--reason`` argument
that gets recorded in ``THREAD_LOG.md``).
"""

from __future__ import annotations

from enum import StrEnum

from swarmlord.core.errors import IllegalTransition


class Stage(StrEnum):
    IDEA = "idea"
    DISCOVERY = "discovery"
    SPEC_READY = "spec_ready"
    BUILD_READY = "build_ready"
    EXTRACTED = "extracted"
    ARCHIVED = "archived"


# Adjacency list: from -> set of legal destinations (forward + back).
LEGAL_TRANSITIONS: dict[Stage, frozenset[Stage]] = {
    Stage.IDEA: frozenset({Stage.DISCOVERY, Stage.ARCHIVED}),
    Stage.DISCOVERY: frozenset({Stage.SPEC_READY, Stage.IDEA, Stage.ARCHIVED}),
    Stage.SPEC_READY: frozenset({Stage.BUILD_READY, Stage.DISCOVERY, Stage.ARCHIVED}),
    Stage.BUILD_READY: frozenset({Stage.EXTRACTED, Stage.SPEC_READY, Stage.ARCHIVED}),
    Stage.EXTRACTED: frozenset({Stage.ARCHIVED}),
    Stage.ARCHIVED: frozenset(),
}

# Forward order, used to derive "next stage" defaults.
FORWARD_ORDER: tuple[Stage, ...] = (
    Stage.IDEA,
    Stage.DISCOVERY,
    Stage.SPEC_READY,
    Stage.BUILD_READY,
    Stage.EXTRACTED,
    Stage.ARCHIVED,
)


def can_transition(from_stage: Stage, to_stage: Stage) -> bool:
    """Return True iff transitioning from ``from_stage`` to ``to_stage`` is allowed."""
    return to_stage in LEGAL_TRANSITIONS[from_stage]


def assert_transition(from_stage: Stage, to_stage: Stage) -> None:
    """Raise :class:`IllegalTransition` if the transition is not legal."""
    if not can_transition(from_stage, to_stage):
        raise IllegalTransition(from_stage.value, to_stage.value)


def next_stage(stage: Stage) -> Stage | None:
    """The next forward stage, or ``None`` if there is no forward step."""
    if stage is Stage.ARCHIVED:
        return None
    idx = FORWARD_ORDER.index(stage)
    if idx + 1 >= len(FORWARD_ORDER) - 1:  # exclude ARCHIVED as a "next"
        return None
    return FORWARD_ORDER[idx + 1]


def is_forward(from_stage: Stage, to_stage: Stage) -> bool:
    """Return True iff ``to_stage`` is strictly after ``from_stage`` in forward order."""
    if to_stage is Stage.ARCHIVED:
        # Archiving is never "forward" in the gated sense; it is always allowed
        # without gates from any stage. Treat as non-forward so promote() does
        # not run gates against it.
        return False
    return FORWARD_ORDER.index(to_stage) > FORWARD_ORDER.index(from_stage)
