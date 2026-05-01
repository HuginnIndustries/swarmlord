"""Predicate evaluator tests."""

from __future__ import annotations

from pathlib import Path

from swarmlord.core.gates import evaluate_predicate
from swarmlord.core.models import (
    ExtractMdResolved,
    FileExists,
    FileSectionFilled,
    YamlFieldEmpty,
    YamlFieldEquals,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_file_exists(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", "hi")
    pos = evaluate_predicate(FileExists(kind="file_exists", path="a.txt"), tmp_path)
    assert pos.passed
    neg = evaluate_predicate(FileExists(kind="file_exists", path="missing"), tmp_path)
    assert not neg.passed


def test_file_section_filled_pass(tmp_path: Path) -> None:
    body = "# Doc\n\n## Outcome\n\nA real outcome with content.\n\n## Next\n"
    _write(tmp_path / "spec.md", body)
    res = evaluate_predicate(
        FileSectionFilled(kind="file_section_filled", path="spec.md", section="## Outcome"),
        tmp_path,
    )
    assert res.passed


def test_file_section_filled_blocks_forbidden_token(tmp_path: Path) -> None:
    body = "# Doc\n\n## Outcome\n\nTBD: not done yet\n"
    _write(tmp_path / "spec.md", body)
    res = evaluate_predicate(
        FileSectionFilled(kind="file_section_filled", path="spec.md", section="## Outcome"),
        tmp_path,
    )
    assert not res.passed
    assert "TBD" in res.message


def test_file_section_filled_handles_empty_section(tmp_path: Path) -> None:
    body = "## Outcome\n\n\n## Next\n"
    _write(tmp_path / "spec.md", body)
    res = evaluate_predicate(
        FileSectionFilled(kind="file_section_filled", path="spec.md", section="## Outcome"),
        tmp_path,
    )
    assert not res.passed


def test_yaml_field_empty(tmp_path: Path) -> None:
    _write(tmp_path / "s.yaml", "open_questions: []\nnested:\n  k: 1\n")
    pos = evaluate_predicate(
        YamlFieldEmpty(kind="yaml_field_empty", path="s.yaml", field="open_questions"),
        tmp_path,
    )
    assert pos.passed
    neg = evaluate_predicate(
        YamlFieldEmpty(kind="yaml_field_empty", path="s.yaml", field="nested.k"),
        tmp_path,
    )
    assert not neg.passed


def test_yaml_field_equals(tmp_path: Path) -> None:
    _write(tmp_path / "s.yaml", "stage: spec_ready\n")
    res = evaluate_predicate(
        YamlFieldEquals(kind="yaml_field_equals", path="s.yaml", field="stage", value="spec_ready"),
        tmp_path,
    )
    assert res.passed
    res_bad = evaluate_predicate(
        YamlFieldEquals(kind="yaml_field_equals", path="s.yaml", field="stage", value="idea"),
        tmp_path,
    )
    assert not res_bad.passed


def test_extract_md_resolved(tmp_path: Path) -> None:
    body = "# Extraction\n\n- [x] item one\n- [-] deferred item\n- [ ] still open\n"
    _write(tmp_path / "EXTRACT.md", body)
    res = evaluate_predicate(ExtractMdResolved(kind="extract_md_resolved"), tmp_path)
    assert not res.passed
    body_ok = "# Extraction\n\n- [x] item one\n- [-] deferred item\n"
    _write(tmp_path / "EXTRACT.md", body_ok)
    res2 = evaluate_predicate(ExtractMdResolved(kind="extract_md_resolved"), tmp_path)
    assert res2.passed


def test_extract_md_resolved_marks_explicit_deferred_text(tmp_path: Path) -> None:
    body = "- [ ] this is deferred for V2\n- [x] done\n"
    _write(tmp_path / "EXTRACT.md", body)
    res = evaluate_predicate(ExtractMdResolved(kind="extract_md_resolved"), tmp_path)
    assert res.passed


def test_path_confinement_blocks_traversal(tmp_path: Path) -> None:
    """Predicates must refuse to read paths outside the packet root."""
    # Create a sibling file the predicate should NOT be allowed to read.
    other = tmp_path.parent / "outside.md"
    other.write_text("# External\n\n## Outcome\n\nshould be unreachable\n", encoding="utf-8")
    res = evaluate_predicate(
        FileSectionFilled(
            kind="file_section_filled",
            path="../outside.md",
            section="## Outcome",
        ),
        tmp_path,
    )
    assert not res.passed
    assert "escapes the packet root" in res.message


def test_path_confinement_allows_in_root(tmp_path: Path) -> None:
    _write(tmp_path / "ok.txt", "hi")
    res = evaluate_predicate(
        FileExists(kind="file_exists", path="ok.txt"),
        tmp_path,
    )
    assert res.passed


def test_yaml_field_path_confinement(tmp_path: Path) -> None:
    """YAML predicates also refuse to escape the packet root."""
    res = evaluate_predicate(
        YamlFieldEmpty(
            kind="yaml_field_empty",
            path="../something.yaml",
            field="x",
        ),
        tmp_path,
    )
    assert not res.passed
    assert "escapes the packet root" in res.message
