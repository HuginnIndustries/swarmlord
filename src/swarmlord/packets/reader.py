"""Load packet artifacts from disk.

Two key entry points: :func:`load_status` for ``workflow/status.yaml`` and
:func:`load_workflow` for ``workflow/WORKFLOW.md``. :func:`load_packet`
returns both bundled together.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import frontmatter
from pydantic import ValidationError
from ruamel.yaml import YAML

from swarmlord.core.errors import PacketSchemaError, WorkflowParseError
from swarmlord.core.models import PacketStatus, WorkflowDefinition

_yaml = YAML(typ="rt")  # round-trip preserves comments & ordering on writes


@dataclass(slots=True, frozen=True)
class PacketBundle:
    root: Path
    status: PacketStatus
    workflow: WorkflowDefinition | None  # None when no WORKFLOW.md present


def load_status(packet_root: Path) -> PacketStatus:
    """Parse ``workflow/status.yaml`` into a :class:`PacketStatus`."""
    status_file = packet_root / "workflow" / "status.yaml"
    if not status_file.is_file():
        raise FileNotFoundError(f"workflow/status.yaml missing under {packet_root}")
    raw = status_file.read_text(encoding="utf-8")
    data = _yaml.load(raw)
    try:
        return PacketStatus.model_validate(data)
    except ValidationError as exc:
        raise PacketSchemaError(
            f"{status_file} failed validation:\n{_format_validation_error(exc)}"
        ) from exc


def load_workflow(packet_root: Path) -> WorkflowDefinition | None:
    """Parse ``workflow/WORKFLOW.md`` if present; return ``None`` otherwise."""
    workflow_file = packet_root / "workflow" / "WORKFLOW.md"
    if not workflow_file.is_file():
        return None
    raw = workflow_file.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    front_matter = dict(post.metadata or {})
    body = post.content or ""
    front_matter["prompt_template"] = body
    try:
        return WorkflowDefinition.model_validate(front_matter)
    except ValidationError as exc:
        raise WorkflowParseError(
            f"{workflow_file} failed validation:\n{_format_validation_error(exc)}"
        ) from exc


def load_packet(packet_root: Path) -> PacketBundle:
    """Load both ``status.yaml`` and (optional) ``WORKFLOW.md``."""
    status = load_status(packet_root)
    workflow = load_workflow(packet_root)
    return PacketBundle(root=packet_root, status=status, workflow=workflow)


def dump_status_yaml(status: PacketStatus) -> str:
    """Serialize a :class:`PacketStatus` to YAML text (strict, deterministic)."""
    payload = status.model_dump(mode="json", exclude_none=True)
    buf = io.StringIO()
    _yaml.dump(payload, buf)
    return buf.getvalue()


def _format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
