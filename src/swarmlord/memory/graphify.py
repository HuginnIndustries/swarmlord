"""Wrap the ``graphify`` CLI as a subprocess.

V1 runs graphify only on demand (``swarmlord graphify <slug>``). Auto-run is
explicitly deferred to V2.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from swarmlord.core.errors import RunnerError
from swarmlord.core.models import MemoryStatus


@dataclass(slots=True, frozen=True)
class GraphifyResult:
    graph_path: Path
    report_path: Path
    generated_at: datetime
    exit_code: int
    stdout: str
    stderr: str

    def as_memory_status(self) -> MemoryStatus:
        return MemoryStatus(
            graph_path=str(self.graph_path),
            report_path=str(self.report_path),
            generated_at=self.generated_at,
        )


def run_graphify(
    target_root: Path,
    *,
    update: bool = False,
    binary: str | None = None,
    extra_args: list[str] | None = None,
) -> GraphifyResult:
    """Run graphify against ``target_root``."""
    binary = binary or shutil.which("graphify") or "graphify"
    cmd: list[str] = [binary]
    if update:
        cmd.append("--update")
    if extra_args:
        cmd.extend(extra_args)
    started = datetime.now(UTC)
    try:
        result = subprocess.run(
            cmd,
            cwd=target_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RunnerError(f"graphify binary not found: {binary}") from exc
    if result.returncode != 0:
        raise RunnerError(
            f"graphify exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )
    out_dir = target_root / "graphify-out"
    report = out_dir / "GRAPH_REPORT.md"
    if not report.is_file():
        raise RunnerError(f"graphify completed but {report} was not produced — check the install")
    return GraphifyResult(
        graph_path=out_dir,
        report_path=report,
        generated_at=started,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
