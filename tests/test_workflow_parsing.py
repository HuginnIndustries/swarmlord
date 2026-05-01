"""Workflow parsing — front matter + body."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarmlord.core.errors import WorkflowParseError
from swarmlord.core.phases import Phase
from swarmlord.packets.reader import load_workflow

GOOD = """---
runner_profile: manual
phase: discovery
gates:
  promote_to_spec_ready:
    - kind: file_section_filled
      path: spec/discovery.md
      section: "## Recommended Direction"
---

Hello {{ packet.slug }}
"""

NO_FM = "Just a body, no front matter\n"

BAD_FM = """---
runner_profile: manual
phase: not_a_phase
---

body
"""


def test_load_workflow_good(tmp_path: Path) -> None:
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "WORKFLOW.md").write_text(GOOD, encoding="utf-8")
    wf = load_workflow(tmp_path)
    assert wf is not None
    assert wf.runner_profile == "manual"
    assert wf.phase is Phase.DISCOVERY
    assert "Hello" in wf.prompt_template
    assert wf.gates.promote_to_spec_ready[0].kind == "file_section_filled"


def test_load_workflow_missing_file(tmp_path: Path) -> None:
    assert load_workflow(tmp_path) is None


def test_load_workflow_no_front_matter_fails(tmp_path: Path) -> None:
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "WORKFLOW.md").write_text(NO_FM, encoding="utf-8")
    with pytest.raises(WorkflowParseError):
        load_workflow(tmp_path)


def test_load_workflow_bad_phase(tmp_path: Path) -> None:
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "WORKFLOW.md").write_text(BAD_FM, encoding="utf-8")
    with pytest.raises(WorkflowParseError):
        load_workflow(tmp_path)
