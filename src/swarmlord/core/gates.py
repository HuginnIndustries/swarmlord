"""Predicate evaluators.

Each predicate has a deterministic evaluator function that takes the packet
root and returns a :class:`GateResult`. Predicates never write state — they
only inspect disk.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from swarmlord.core.models import (
    ExtractMdResolved,
    FileExists,
    FileSectionFilled,
    Predicate,
    TestsPassing,
    YamlFieldEmpty,
    YamlFieldEquals,
)

_yaml = YAML(typ="safe")


@dataclass(slots=True, frozen=True)
class GateResult:
    """Outcome of evaluating one predicate."""

    predicate: Predicate
    passed: bool
    message: str

    @property
    def label(self) -> str:
        kind = getattr(self.predicate, "kind", "?")
        path = getattr(self.predicate, "path", "")
        return f"{kind}({path})" if path else str(kind)


def evaluate_predicate(predicate: Predicate, packet_root: Path) -> GateResult:
    """Dispatch a single predicate to its evaluator."""
    match predicate:
        case FileExists():
            return _eval_file_exists(predicate, packet_root)
        case FileSectionFilled():
            return _eval_file_section_filled(predicate, packet_root)
        case YamlFieldEmpty():
            return _eval_yaml_field_empty(predicate, packet_root)
        case YamlFieldEquals():
            return _eval_yaml_field_equals(predicate, packet_root)
        case ExtractMdResolved():
            return _eval_extract_md_resolved(predicate, packet_root)
        case TestsPassing():
            return _eval_tests_passing(predicate, packet_root)


def evaluate_gate(predicates: list[Predicate], packet_root: Path) -> list[GateResult]:
    """Evaluate every predicate in order. Returns one :class:`GateResult` per."""
    return [evaluate_predicate(p, packet_root) for p in predicates]


# --- evaluators ----------------------------------------------------------


def _eval_file_exists(p: FileExists, root: Path) -> GateResult:
    target = root / p.path
    if target.is_file():
        return GateResult(p, True, f"{p.path} exists")
    return GateResult(p, False, f"{p.path} is missing under {root}")


def _eval_file_section_filled(p: FileSectionFilled, root: Path) -> GateResult:
    target = root / p.path
    if not target.is_file():
        return GateResult(p, False, f"{p.path} is missing")
    text = target.read_text(encoding="utf-8")
    body = _extract_section(text, p.section)
    if body is None:
        return GateResult(p, False, f"{p.path} has no section '{p.section}'")
    stripped = body.strip()
    if not stripped:
        return GateResult(p, False, f"{p.path} '{p.section}' is empty")
    for token in p.forbidden_tokens:
        # Match token as a whole word, case-sensitive (forbidden tokens are
        # explicit markers like TBD/TODO/FIXME — we want them caught even when
        # tucked inside prose).
        if re.search(rf"\b{re.escape(token)}\b", stripped):
            return GateResult(
                p,
                False,
                f"{p.path} '{p.section}' contains forbidden token '{token}'",
            )
    return GateResult(p, True, f"{p.path} '{p.section}' is filled")


def _eval_yaml_field_empty(p: YamlFieldEmpty, root: Path) -> GateResult:
    value, msg = _load_yaml_field(p.path, p.field, root)
    if msg is not None:
        return GateResult(p, False, msg)
    if _is_empty(value):
        return GateResult(p, True, f"{p.path}::{p.field} is empty")
    return GateResult(p, False, f"{p.path}::{p.field} is not empty (has value: {value!r})")


def _eval_yaml_field_equals(p: YamlFieldEquals, root: Path) -> GateResult:
    value, msg = _load_yaml_field(p.path, p.field, root)
    if msg is not None:
        return GateResult(p, False, msg)
    if value == p.value:
        return GateResult(p, True, f"{p.path}::{p.field} == {p.value!r}")
    return GateResult(p, False, f"{p.path}::{p.field} == {value!r}, expected {p.value!r}")


def _eval_extract_md_resolved(p: ExtractMdResolved, root: Path) -> GateResult:
    target = root / "EXTRACT.md"
    if not target.is_file():
        return GateResult(p, False, "EXTRACT.md is missing")
    text = target.read_text(encoding="utf-8")
    unresolved = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^\s*-\s*\[\s*( |x|X|-)?\s*\]", line)
        if not m:
            continue
        marker = (m.group(1) or " ").lower()
        if marker == "x":
            continue
        # "-" is treated as explicitly deferred.
        if marker == "-":
            continue
        # blank checkbox -> still open
        suffix = line[m.end() :].strip().lower()
        if "deferred" in suffix or "n/a" in suffix:
            continue
        unresolved.append(f"line {lineno}: {line.strip()}")
    if unresolved:
        sample = unresolved[0]
        return GateResult(
            p,
            False,
            f"EXTRACT.md has {len(unresolved)} unresolved checkbox(es); first: {sample}",
        )
    return GateResult(p, True, "EXTRACT.md checkboxes all resolved or deferred")


def _eval_tests_passing(p: TestsPassing, root: Path) -> GateResult:
    try:
        result = subprocess.run(
            p.command,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return GateResult(p, False, f"tests timed out: `{p.command}`")
    if result.returncode == 0:
        return GateResult(p, True, f"tests passed: `{p.command}`")
    tail = (result.stderr or result.stdout or "").strip().splitlines()[-3:]
    return GateResult(
        p, False, f"tests failed (exit {result.returncode}): `{p.command}` :: {' / '.join(tail)}"
    )


# --- helpers -------------------------------------------------------------


def _extract_section(text: str, header: str) -> str | None:
    """Return the body under ``header`` (a markdown heading, e.g. '## Outcome').

    The body ends at the next heading of equal or shallower level, or EOF.
    """
    header_level = len(header) - len(header.lstrip("#"))
    if header_level == 0:
        return None
    pattern = re.compile(rf"^{re.escape(header)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    start = m.end()
    next_header = re.compile(rf"^#{{1,{header_level}}}\s+\S", re.MULTILINE)
    nm = next_header.search(text, pos=start)
    return text[start : nm.start() if nm else len(text)]


def _load_yaml_field(rel_path: str, dotted: str, root: Path) -> tuple[Any, str | None]:
    target = root / rel_path
    if not target.is_file():
        return None, f"{rel_path} is missing"
    try:
        data = _yaml.load(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{rel_path} could not be parsed: {exc}"
    cur: Any = data
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, f"{rel_path}::{dotted} is not present"
    return cur, None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str | list | dict | tuple | set):
        return len(value) == 0
    return False
