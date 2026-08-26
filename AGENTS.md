# Agent Guide — SwarmLord Codebase

This is the implementation repo for SwarmLord. It is **not** a project packet — packets live under `projects/` and are operated on by this CLI.

## Setup

```sh
git clone https://github.com/HuginnIndustries/swarmlord.git
cd swarmlord
uv sync --dev

make check              # ruff check + ruff format --check + mypy --strict + pytest
uv run swarmlord --help
```

Or run the gates individually:

```sh
uv run ruff check
uv run ruff format --check          # drop --check to auto-format
uv run mypy --strict src/swarmlord
uv run pytest                       # 98 tests, ~85% coverage; gate is 80%
```

Architecture layers (`src/swarmlord/core`, `packets`, `templating`, `runners`, `memory`, `storage`, `service`, `cli`) are all wired and pass `mypy --strict`.

## First read

In order:

1. `README.md` — what SwarmLord is, how the state machine and gates work, and the entry point for new contributors.
2. `spec/build-spec.md` — the original implementation contract: architecture layers, Pydantic schemas, runner protocol, CLI surface, acceptance criteria, test plan. It is a **historical design record**, not a live roadmap; where it describes hosted or multi-tenant phases, those are dropped (see *Scope* below). Where it describes the shipped V1 architecture, treat it as the contract and don't re-decide it.
3. `spec/inspiration-review.md` — only if you want the trade-off reasoning that led to the spec's choices.
4. `THREAD_LOG.md` — running handoff log; read the most recent few entries to know what last happened.

## Scope

SwarmLord is a local, single-user CLI and Python library. There is no hosted service, no HTTP server, and no multi-tenancy — those phases were considered during design and dropped. Don't add a server module, an auth layer, or tenant concepts. Work that sharpens the local tool is in scope.

## What is settled

Locked in by `spec/build-spec.md` and `spec/discovery.md`. Do not relitigate without explicit user direction:

- Language: Python 3.12, managed via `uv`.
- Schema layer: Pydantic v2 (replaces the natural-language `pipeline.yaml` the early design imagined).
- Templating: Jinja2 with `StrictUndefined`.
- CLI: Typer.
- Storage: SQLite at the platform data dir (`~/.local/share/swarmlord/runs.db` on POSIX).
- Runners: manual, claude-code-interactive, sandcastle-docker. Sandcastle is invoked as a subprocess, not imported as a Node module.
- State machine: stages and phases as code-defined enums; transitions guarded by typed predicate gates.
- Memory layer: Graphify on demand via `swarmlord graphify`.
- Brand: SwarmLord. Package and CLI binary are both `swarmlord`, with `swarm` as an alias.

## What's open

- The exact shape of the `tests_passing` predicate's sandboxed exec. Today it runs the command directly in the packet root with `shell=True`.
- Real `claude-code-interactive` and `sandcastle-docker` smoke tests against the actual binaries. CI mocks both.
- Broader predicate vocabulary — new `kind:` values are additive and welcome if a real packet needs them.

## Working conventions

- Atomic packet writes use temp-file-and-rename. Never write to `status.yaml` or `THREAD_LOG.md` mid-stream — go through `packets/writer.py` and `packets/thread_log.py`.
- All template rendering uses `StrictUndefined`. User-supplied content is inserted as already-rendered strings; the template engine never re-evaluates user data.
- `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest --cov` must all pass before merging.
- Coverage gate is 80% globally. `runners/claude_code.py` is omitted — it shells out to a binary CI can't run.
- Convert relative dates to absolute `YYYY-MM-DD` before persisting anything user-visible.

## Session protocol

When starting:

1. Read this file, then the relevant part of `spec/build-spec.md`.
2. Pick one focused change. Confirm scope in an issue if it's more than a fix.

When finishing meaningful work:

1. Update relevant code and tests; run `make check`.
2. Append a short handoff entry to `THREAD_LOG.md`.
3. If user-visible, add a `CHANGELOG.md` entry under `[Unreleased]`.

## Origin

This codebase was extracted from a packet in a personal side-project backlog — the same packet format the CLI now operates. The full design history (idea → discovery → inspiration review → build spec) lives in `spec/`.
