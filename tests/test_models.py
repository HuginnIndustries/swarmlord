"""Schema tests for PacketStatus and the predicate union."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from swarmlord.core.models import (
    AgentConfig,
    GateConfig,
    PacketStatus,
    WorkflowDefinition,
    WorkflowHooks,
)
from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage


def test_packetstatus_minimal_valid() -> None:
    s = PacketStatus(
        project_name="p",
        slug="2026-05-p",
        stage=Stage.IDEA,
        current_phase=Phase.IDEA,
        created=date(2026, 5, 1),
        updated=date(2026, 5, 1),
    )
    assert s.summary == ""
    assert s.next_actions == []
    assert s.resolved_questions == []


def test_packetstatus_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        PacketStatus.model_validate(
            {
                "project_name": "p",
                "slug": "p",
                "stage": "idea",
                "current_phase": "idea",
                "created": "2026-05-01",
                "updated": "2026-05-01",
                "wat": True,
            }
        )


def test_packetstatus_rejects_bad_stage() -> None:
    with pytest.raises(ValidationError):
        PacketStatus.model_validate(
            {
                "project_name": "p",
                "slug": "p",
                "stage": "DEFINITELY_NOT_A_STAGE",
                "current_phase": "idea",
                "created": "2026-05-01",
                "updated": "2026-05-01",
            }
        )


def test_phase_status_keys_coerce_from_strings() -> None:
    s = PacketStatus.model_validate(
        {
            "project_name": "p",
            "slug": "p",
            "stage": "idea",
            "current_phase": "idea",
            "created": "2026-05-01",
            "updated": "2026-05-01",
            "phase_status": {"idea": "pending", "discovery": "complete"},
        }
    )
    assert s.phase_status[Phase.IDEA] == "pending"
    assert s.phase_status[Phase.DISCOVERY] == "complete"


def test_predicate_discriminator() -> None:
    cfg = GateConfig.model_validate(
        {
            "promote_to_spec_ready": [
                {
                    "kind": "file_section_filled",
                    "path": "spec/discovery.md",
                    "section": "## Recommended Direction",
                }
            ],
            "promote_to_build_ready": [
                {"kind": "yaml_field_empty", "path": "x.yaml", "field": "open"}
            ],
        }
    )
    assert cfg.promote_to_spec_ready[0].kind == "file_section_filled"
    assert cfg.promote_to_build_ready[0].kind == "yaml_field_empty"


def test_workflow_definition_defaults() -> None:
    wf = WorkflowDefinition(
        runner_profile="manual",
        phase=Phase.DISCOVERY,
        prompt_template="hi",
    )
    assert isinstance(wf.hooks, WorkflowHooks)
    assert isinstance(wf.agent, AgentConfig)
    assert wf.agent.max_turns == 20


def test_packetstatus_accepts_extraction_metadata() -> None:
    s = PacketStatus.model_validate(
        {
            "project_name": "p",
            "slug": "p",
            "stage": "extracted",
            "current_phase": "extraction",
            "created": "2026-05-01",
            "updated": "2026-05-01",
            "extracted_to": "~/Documents/GitHub/p",
            "extracted_on": "2026-05-01",
        }
    )
    assert s.extracted_to == "~/Documents/GitHub/p"
    assert s.extracted_on == date(2026, 5, 1)


def test_owner_notes_coerces_non_string_items() -> None:
    """Real-world packets sometimes have non-string items mixed in."""
    s = PacketStatus.model_validate(
        {
            "project_name": "p",
            "slug": "p",
            "stage": "idea",
            "current_phase": "idea",
            "created": "2026-05-01",
            "updated": "2026-05-01",
            "owner_notes": ["a real note", None, 42, {"nested": "dict"}],
        }
    )
    assert s.owner_notes[0] == "a real note"
    assert s.owner_notes[1] == ""  # None coerces to empty string
    assert s.owner_notes[2] == "42"
    assert s.owner_notes[3] == "{'nested': 'dict'}"


def test_string_list_coercion_applies_to_other_lists() -> None:
    s = PacketStatus.model_validate(
        {
            "project_name": "p",
            "slug": "p",
            "stage": "idea",
            "current_phase": "idea",
            "created": "2026-05-01",
            "updated": "2026-05-01",
            "open_questions": [None, 1, "real"],
        }
    )
    assert s.open_questions == ["", "1", "real"]
