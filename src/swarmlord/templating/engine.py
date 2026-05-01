"""Jinja2 engine wrapper with StrictUndefined and fixed config.

Templates live in ``WORKFLOW.md`` bodies. They are rendered against a typed
:class:`PromptContext`. The engine deliberately disables autoescape (we are
generating Markdown, not HTML) and uses ``keep_trailing_newline=True`` so
template authors don't have to fight the renderer's whitespace handling.

User-supplied content (open question text, owner notes, etc.) is fed to the
template as already-rendered strings — the template engine is given the
final text and never sees a second pass over it. That is why a question
containing ``{{ x }}`` survives intact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import TemplateError

from swarmlord.core.errors import TemplateRenderError
from swarmlord.core.models import PacketStatus
from swarmlord.templating.filters import default_empty, indent_filter, summarize, trim_filter

_ENV = Environment(
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
    trim_blocks=False,
    lstrip_blocks=False,
)
_ENV.filters["trim"] = trim_filter
_ENV.filters["indent_n"] = indent_filter
_ENV.filters["default_empty"] = default_empty
_ENV.filters["summarize"] = summarize


@dataclass(slots=True)
class PromptContext:
    """The variables exposed to a prompt template."""

    packet: PacketStatus
    repo_root: Path
    packet_root: Path
    attempt: int = 0
    prior_run_summary: str = ""
    graph_report_path: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "packet": self.packet,
            "repo_root": str(self.repo_root),
            "packet_root": str(self.packet_root),
            "attempt": self.attempt,
            "prior_run_summary": self.prior_run_summary,
            "graph_report_path": self.graph_report_path,
        }
        base.update(self.extras)
        return base


def build_context(
    packet: PacketStatus,
    *,
    repo_root: Path,
    packet_root: Path,
    attempt: int = 0,
    prior_run_summary: str = "",
    graph_report_path: str | None = None,
    extras: dict[str, Any] | None = None,
) -> PromptContext:
    return PromptContext(
        packet=packet,
        repo_root=repo_root,
        packet_root=packet_root,
        attempt=attempt,
        prior_run_summary=prior_run_summary,
        graph_report_path=graph_report_path,
        extras=extras or {},
    )


def render_string(template_text: str, context: PromptContext) -> str:
    """Render a Jinja2 template *body* (no front matter) against the context."""
    try:
        template = _ENV.from_string(template_text)
        return template.render(**context.as_dict())
    except TemplateError as exc:
        raise TemplateRenderError(str(exc)) from exc


def render_prompt(
    template_text: str,
    packet: PacketStatus,
    *,
    repo_root: Path,
    packet_root: Path,
    attempt: int = 0,
    prior_run_summary: str = "",
    graph_report_path: str | None = None,
    extras: dict[str, Any] | None = None,
) -> str:
    """Convenience wrapper: build the context and render in one call."""
    context = build_context(
        packet,
        repo_root=repo_root,
        packet_root=packet_root,
        attempt=attempt,
        prior_run_summary=prior_run_summary,
        graph_report_path=graph_report_path,
        extras=extras,
    )
    return render_string(template_text, context)
