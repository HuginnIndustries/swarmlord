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
