# Agent Guide — SwarmLord Codebase

This is the implementation repo for SwarmLord. It is **not** a project packet (packets live elsewhere; this codebase scaffolds and operates them).

## Setup

V1 is implemented. Standard workflow:

```powershell
cd ~\Documents\GitHub\swarmlord
uv sync --dev
uv run pytest          # 94 tests, ~85% coverage
uv run ruff check
uv run ruff format --check
uv run mypy --strict src/swarmlord
uv run swarmlord --help
```

Architecture layers (`src/swarmlord/core`, `packets`, `templating`, `runners`, `memory`, `storage`, `service`, `cli`, `server`) are all wired and pass `mypy --strict`. The FastAPI `server/` module is a V2 scaffold that returns 501 from every endpoint — the import paths are stable so V2 can fill in the bodies without restructuring.

CLI entry points (already in `pyproject.toml`):

```toml
[project.scripts]
swarmlord = "swarmlord.cli:app"
swarm = "swarmlord.cli:app"
```

### Optional — mirror to a self-hosted git server

If you want to keep GitHub as the primary surface and also push to a personal forge (Gitea, Forgejo, etc.), add the second URL as an additional push target on `origin`:

```powershell
git remote set-url --add --push origin https://github.com/TheAmericanMaker/swarmlord.git
git remote set-url --add --push origin ssh://git@<forge-host>:<port>/<owner>/swarmlord.git
git remote -v   # one (fetch) line, two (push) lines
```

After that, every `git push origin main` mirrors to both. The forge repo must exist before the first push.

## First read

In order:

1. `README.md` — what SwarmLord is, the v1/v2/v3 roadmap, and the entry point for new contributors.
2. `spec/build-spec.md` — the implementation-ready spec. Outcome, user workflows, architecture layers, Pydantic schemas, runner protocol, CLI surface, acceptance criteria, test plan, V2/V3 outline. **Treat this as the contract.** Do not re-decide architecture.
3. `spec/inspiration-review.md` — only if you want the trade-off reasoning that led to the spec's choices.
4. `THREAD_LOG.md` — running handoff log; read the most recent few entries to know what last happened.

## What is settled

These choices are locked in by `spec/build-spec.md` and `spec/discovery.md`. Do not relitigate without explicit user direction:

- Language: Python 3.12, managed via `uv`.
- Schema layer: Pydantic v2 (replaces the natural-language `pipeline.yaml`).
- Templating: Jinja2 with `StrictUndefined`.
- CLI: Typer.
- Storage (V1): SQLite at `~/.local/share/swarmlord/runs.db`. Postgres in V2.
- Runners (V1): manual, claude-code-interactive, sandcastle-docker (Sandcastle invoked as a subprocess, not as a Node import).
- State machine: stages and phases as code-defined enums; transitions guarded by typed predicate gates.
- Memory layer: Graphify on demand via `swarmlord graphify`. Auto-run is V2.
- Server: FastAPI scaffold in v1 (stubs returning 501); endpoints in V2.
- Brand: SwarmLord. Domain `swarmlord.dev` is owned. Package and CLI both `swarmlord`.

## What's open

- The exact shape of the `tests_passing` predicate's sandboxed exec (V2-relevant; V1 runs the command directly in the packet root with `shell=True`).
- V2 server bodies (FastAPI routes), arq worker queue wiring, Postgres/SQLAlchemy migration.
- V3 multi-tenancy decisions: tenant isolation strategy, billing model, SSO surface.
- Real `claude-code-interactive` and `sandcastle-docker` smoke tests against the actual binaries (CI mocks both).

## Working conventions

- Atomic packet writes use temp-file-and-rename. Never write to `status.yaml` or `THREAD_LOG.md` mid-stream.
- All template rendering uses `StrictUndefined`. User-supplied content is inserted as already-rendered strings; the template engine never re-evaluates user data.
- `mypy --strict`, `ruff check`, `ruff format --check`, and `pytest --cov` must all pass before merging.
- Coverage gate: 80% on `core/`, `packets/`, `templating/`, and the gate evaluators.

## Session protocol

When starting:

1. Read this file, then `spec/build-spec.md`.
2. Pick a milestone from the spec's Acceptance Criteria. The dogfood-first milestone is `swarmlord list` and `swarmlord render` working against the originating packet (`side-projects/projects/2026-05-sandcastle-like-agent-orchestration/`).
3. Implement, test, document.

When finishing meaningful work:

1. Update relevant code and tests.
2. Append a short handoff entry to `THREAD_LOG.md`.
3. If a major milestone lands, update `README.md` Status.

## Origin

This codebase was extracted from the packet `2026-05-sandcastle-like-agent-orchestration` in a `side-projects` backlog repo. The full design history (idea → discovery → inspiration review → build spec) lives in `spec/` and is the canonical source for how the architecture was chosen.
