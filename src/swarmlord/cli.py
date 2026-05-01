"""Typer entry point — thin shell over :mod:`swarmlord.service`.

The CLI handles argument parsing, output formatting, and exit codes. All
logic that is not strictly UI lives in the service module so the V2 HTTP
surface can call the same functions without going through Typer.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from swarmlord import __version__
from swarmlord.core.errors import GateFailure, SwarmLordError
from swarmlord.core.phases import Phase
from swarmlord.core.stages import Stage
from swarmlord.memory.graphify import run_graphify
from swarmlord.packets.reader import load_packet
from swarmlord.packets.writer import write_status
from swarmlord.runners.claude_code import ClaudeCodeInteractiveRunner
from swarmlord.runners.manual import ManualRunner
from swarmlord.runners.registry import RunnerRegistry
from swarmlord.runners.sandcastle import SandcastleDockerRunner
from swarmlord.service import (
    NewPacketSpec,
    dispatch_run,
    extract_packet,
    list_packets,
    new_packet,
    pick_next,
    promote,
    render_for_packet,
    resolve_packet,
    validate_all,
    validate_packet,
)
from swarmlord.storage.run_history import RunHistory

app = typer.Typer(
    name="swarmlord",
    help="Orchestrator for project packets — coordinates a swarm of agent-workers.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


def _repo_root() -> Path:
    return Path.cwd()


def _fail(msg: str, code: int = 1) -> None:
    err_console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code=code)


def _handle(exc: BaseException) -> None:
    if isinstance(exc, GateFailure):
        err_console.print("[red]gates failed:[/red]")
        for msg in exc.failures:
            err_console.print(f"  - {msg}")
        raise typer.Exit(code=2) from exc
    if isinstance(exc, SwarmLordError):
        _fail(str(exc))
    raise exc


def _print_version(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
        callback=_print_version,
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_cmd(
    stage: Stage | None = typer.Option(None, "--stage"),
    phase: Phase | None = typer.Option(None, "--phase"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List every packet under ./projects with stages and phases."""
    try:
        packets = list_packets(_repo_root(), stage=stage, phase=phase)
    except SwarmLordError as exc:
        _handle(exc)
        return
    if json_out:
        console.print_json(
            data=[
                {
                    "slug": p.status.slug,
                    "stage": p.status.stage.value,
                    "phase": p.status.current_phase.value,
                    "summary": p.status.summary,
                    "runner_profile": p.status.runner_profile,
                    "root": str(p.root),
                }
                for p in packets
            ]
        )
        return
    if not packets:
        console.print("[dim]no packets found under ./projects[/dim]")
        return
    table = Table(title=f"packets ({len(packets)})")
    # Slug must always be fully readable — it's the identifier the user types
    # into every other command. Fold across multiple lines instead of truncating.
    table.add_column("slug", overflow="fold", no_wrap=False)
    table.add_column("stage")
    table.add_column("phase")
    table.add_column("runner")
    table.add_column("summary", overflow="fold")
    for p in packets:
        summary = p.status.summary
        table.add_row(
            p.status.slug,
            p.status.stage.value,
            p.status.current_phase.value,
            p.status.runner_profile or "-",
            summary[:80] + ("…" if len(summary) > 80 else ""),
        )
    console.print(table)
    # Surface packets whose status.yaml exists but fails schema validation.
    # Without this, broken packets are silently invisible to the user.
    from swarmlord.packets.discovery import discover_failures

    failures = discover_failures(_repo_root())
    if failures:
        err_console.print(
            f"[yellow]{len(failures)} packet(s) failed schema validation "
            f"(run `swarmlord validate <slug>` for details):[/yellow]"
        )
        for root, msg in failures:
            err_console.print(f"  [yellow]invalid[/yellow] {root.name}: {msg}")


@app.command("next")
def next_cmd(
    stage: Stage | None = typer.Option(None, "--stage"),
    runner_profile: str | None = typer.Option(None, "--runner-profile"),
) -> None:
    """Print the top dispatchable packet and its first next action."""
    packet = pick_next(_repo_root(), stage=stage, runner_profile=runner_profile)
    if packet is None:
        console.print("[dim]nothing dispatchable[/dim]")
        return
    console.print(f"[bold]{packet.status.slug}[/bold] ({packet.status.stage.value})")
    console.print(f"  next: {packet.status.next_actions[0]}")
    if packet.status.runner_profile:
        console.print(f"  runner: {packet.status.runner_profile}")


@app.command("new")
def new_cmd(
    slug: str = typer.Argument(...),
    title: str = typer.Option("", "--title"),
    summary: str = typer.Option("", "--summary"),
    runner_profile: str | None = typer.Option(None, "--runner-profile"),
) -> None:
    """Scaffold a new packet under ./projects/YYYY-MM-<slug>/."""
    spec = NewPacketSpec(
        slug=slug,
        title=title,
        summary=summary,
        repo_root=_repo_root(),
        today=date.today(),
        runner_profile=runner_profile,
    )
    try:
        target = new_packet(spec)
    except SwarmLordError as exc:
        _handle(exc)
        return
    console.print(f"[green]created[/green] {target}")


@app.command("render")
def render_cmd(
    slug: str = typer.Argument(...),
    phase: Phase | None = typer.Option(None, "--phase"),
    attempt: int = typer.Option(0, "--attempt"),
    clipboard: bool = typer.Option(False, "--clipboard"),
) -> None:
    """Render the prompt for a packet's current (or specified) phase."""
    try:
        bundle = resolve_packet(_repo_root(), slug)
        rendered = render_for_packet(_repo_root(), bundle, phase=phase, attempt=attempt)
    except SwarmLordError as exc:
        _handle(exc)
        return
    if clipboard:
        try:
            import pyperclip

            pyperclip.copy(rendered)
            console.print(f"[dim]copied {len(rendered)} chars to clipboard[/dim]")
        except Exception as exc:
            err_console.print(f"[yellow]clipboard unavailable:[/yellow] {exc}")
            console.print(rendered, end="")
    else:
        console.print(rendered, end="", soft_wrap=True, highlight=False)


def _cli_registry() -> RunnerRegistry:
    """Build a CLI-flavored registry that surfaces clipboard warnings to stderr."""
    return RunnerRegistry(
        [
            ManualRunner(
                warn_writer=lambda msg: err_console.print(f"[yellow]{msg}[/yellow]"),
            ),
            ClaudeCodeInteractiveRunner(),
            SandcastleDockerRunner(),
        ]
    )


@app.command("run")
def run_cmd(
    slug: str = typer.Argument(...),
    runner: str | None = typer.Option(None, "--runner"),
    attempt: int = typer.Option(0, "--attempt"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Render and dispatch a run via the requested runner."""
    try:
        bundle = resolve_packet(_repo_root(), slug)
        if dry_run:
            rendered = render_for_packet(_repo_root(), bundle, attempt=attempt)
            console.print(
                f"[dim]would dispatch {len(rendered)} chars to {runner or '(default)'}[/dim]"
            )
            return
        history = RunHistory()
        result, record = asyncio.run(
            dispatch_run(
                _repo_root(),
                bundle,
                runner_profile=runner,
                attempt=attempt,
                registry=_cli_registry(),
                history=history,
            )
        )
    except SwarmLordError as exc:
        _handle(exc)
        return
    console.print(
        f"[green]ran[/green] {record.runner_profile} "
        f"(exit={result.exit_code}, signal={result.completion_signal_seen or '-'})"
    )


@app.command("promote")
def promote_cmd(
    slug: str = typer.Argument(...),
    to: Stage | None = typer.Option(None, "--to"),
    reason: str | None = typer.Option(None, "--reason"),
    demote: bool = typer.Option(False, "--demote"),
) -> None:
    """Evaluate gate predicates and transition a packet's stage."""
    try:
        bundle = resolve_packet(_repo_root(), slug)
        result = promote(_repo_root(), bundle, to=to, reason=reason, demote=demote)
    except (SwarmLordError, GateFailure) as exc:
        _handle(exc)
        return
    history = RunHistory()
    history.record_gate_evaluations(bundle.status.slug, result.gate_results)
    history.record_transition(
        bundle.status.slug,
        result.from_stage.value,
        result.to_stage.value,
        reason=reason,
    )
    console.print(
        f"[green]promoted[/green] {bundle.status.slug}: "
        f"{result.from_stage.value} -> {result.to_stage.value}"
    )
    for gr in result.gate_results:
        marker = "[green]ok[/green]" if gr.passed else "[red]fail[/red]"
        console.print(f"  {marker} {gr.message}")


@app.command("validate")
def validate_cmd(
    slug: str | None = typer.Argument(None),
    all_: bool = typer.Option(False, "--all"),
) -> None:
    """Schema-validate one packet or every packet on disk."""
    if all_:
        rows = validate_all(_repo_root())
        any_failed = False
        for root, err in rows:
            if err is None:
                console.print(f"[green]ok[/green]  {root.name}")
            else:
                any_failed = True
                err_console.print(f"[red]fail[/red] {root.name}: {err}")
        if any_failed:
            raise typer.Exit(code=1)
        return
    if slug is None:
        _fail("provide a slug or pass --all")
        return
    try:
        bundle = resolve_packet(_repo_root(), slug)
        validate_packet(bundle.root)
    except SwarmLordError as exc:
        _handle(exc)
        return
    console.print(f"[green]ok[/green] {bundle.status.slug}")


@app.command("graphify")
def graphify_cmd(
    slug: str | None = typer.Argument(None),
    repo: bool = typer.Option(False, "--repo"),
    update: bool = typer.Option(False, "--update"),
) -> None:
    """Wrap the graphify CLI to build/refresh memory."""
    if repo:
        target = _repo_root()
    elif slug is not None:
        try:
            bundle = resolve_packet(_repo_root(), slug)
        except SwarmLordError as exc:
            _handle(exc)
            return
        target = bundle.root
    else:
        _fail("provide a slug or pass --repo")
        return
    try:
        result = run_graphify(target, update=update)
    except SwarmLordError as exc:
        _handle(exc)
        return
    console.print(f"[green]graphify[/green] -> {result.report_path}")
    if slug is not None:
        bundle = resolve_packet(_repo_root(), slug)
        new_status = bundle.status.model_copy(
            update={"memory": result.as_memory_status(), "updated": date.today()}
        )
        write_status(bundle.root, new_status)


@app.command("extract")
def extract_cmd(
    slug: str = typer.Argument(...),
    target: Path = typer.Option(..., "--target"),
    no_git: bool = typer.Option(False, "--no-git"),
    force: bool = typer.Option(False, "--force", help="Skip stage + ExtractMdResolved gates."),
) -> None:
    """Execute EXTRACT.md into a new repo path and mark the packet extracted."""
    try:
        bundle = resolve_packet(_repo_root(), slug)
        result = extract_packet(
            _repo_root(),
            bundle,
            target=target,
            init_git=not no_git,
            force=force,
        )
    except (SwarmLordError, GateFailure) as exc:
        _handle(exc)
        return
    console.print(
        f"[green]extracted[/green] {bundle.status.slug} -> {result.target} "
        f"({result.files_copied} files)"
    )


@app.command("repair")
def repair_cmd(
    slug: str = typer.Argument(...),
) -> None:
    """Re-derive consistent state from disk after a partial-write failure."""
    target_root = (_repo_root() / "projects" / slug).resolve()
    try:
        bundle = load_packet(target_root)
    except SwarmLordError as exc:
        _handle(exc)
        return
    write_status(bundle.root, bundle.status)
    console.print(f"[green]repaired[/green] {bundle.status.slug}")


@app.command("log")
def log_cmd(
    slug: str = typer.Argument(...),
    limit: int = typer.Option(20, "--limit", help="Most recent N runs."),
    gates: bool = typer.Option(False, "--gates", help="Also show gate evaluations."),
    transitions: bool = typer.Option(False, "--transitions", help="Also show stage transitions."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of tables."),
) -> None:
    """Show run history, gate evaluations, and transitions for a packet."""
    try:
        bundle = resolve_packet(_repo_root(), slug)
    except SwarmLordError as exc:
        _handle(exc)
        return
    history = RunHistory()
    runs = history.list_runs(bundle.status.slug, limit=limit)
    gate_rows = history.list_gate_evaluations(bundle.status.slug) if gates else []
    transition_rows = history.list_transitions(bundle.status.slug) if transitions else []

    if json_out:
        console.print_json(
            data={
                "slug": bundle.status.slug,
                "runs": runs,
                "gates": gate_rows,
                "transitions": transition_rows,
            }
        )
        return

    if not runs and not gate_rows and not transition_rows:
        console.print(f"[dim]no history yet for {bundle.status.slug}[/dim]")
        return

    if runs:
        table = Table(title=f"runs for {bundle.status.slug} ({len(runs)})")
        table.add_column("started", overflow="fold")
        table.add_column("runner")
        table.add_column("phase")
        table.add_column("exit", justify="right")
        table.add_column("status")
        table.add_column("signal", overflow="fold")
        table.add_column("error", overflow="fold")
        for r in runs:
            exit_code = r.get("exit_code")
            status = str(r.get("status") or "")
            status_styled = (
                f"[green]{status}[/green]"
                if status == "succeeded"
                else f"[red]{status}[/red]"
                if status == "failed"
                else status
            )
            table.add_row(
                str(r.get("started_at") or "")[:19],
                str(r.get("runner_profile") or ""),
                str(r.get("phase") or ""),
                "-" if exit_code is None else str(exit_code),
                status_styled,
                str(r.get("completion_signal_seen") or "-"),
                str(r.get("error") or ""),
            )
        console.print(table)

    if gate_rows:
        gtable = Table(title=f"gate evaluations ({len(gate_rows)})")
        gtable.add_column("evaluated", overflow="fold")
        gtable.add_column("predicate", overflow="fold")
        gtable.add_column("result")
        gtable.add_column("message", overflow="fold")
        for g in gate_rows:
            passed = bool(g.get("passed"))
            gtable.add_row(
                str(g.get("evaluated_at") or "")[:19],
                str(g.get("predicate") or ""),
                "[green]pass[/green]" if passed else "[red]fail[/red]",
                str(g.get("message") or ""),
            )
        console.print(gtable)

    if transition_rows:
        ttable = Table(title=f"transitions ({len(transition_rows)})")
        ttable.add_column("at", overflow="fold")
        ttable.add_column("from")
        ttable.add_column("to")
        ttable.add_column("reason", overflow="fold")
        for t in transition_rows:
            ttable.add_row(
                str(t.get("at") or "")[:19],
                str(t.get("from_stage") or ""),
                str(t.get("to_stage") or ""),
                str(t.get("reason") or "-"),
            )
        console.print(ttable)


@app.command("serve")
def serve_cmd(
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Start the FastAPI server (V2)."""
    err_console.print("[yellow]serve is a V2 feature; the server module is a stub in V1.[/yellow]")
    raise typer.Exit(code=2)


def main() -> None:  # pragma: no cover - thin shim
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
