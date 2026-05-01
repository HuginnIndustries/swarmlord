# Agent Guide — SwarmLord Codebase

This is the implementation repo for SwarmLord. It is **not** a project packet (packets live elsewhere; this codebase scaffolds and operates them).

## Setup (start v1 here)

The repo is initialized and pushed to GitHub at [`TheAmericanMaker/swarmlord`](https://github.com/TheAmericanMaker/swarmlord). To begin v1 implementation:

1. Scaffold the package layout with uv:

   ```powershell
   cd ~\Documents\GitHub\swarmlord
   uv init --package
   ```

   This creates `pyproject.toml` and `src/swarmlord/__init__.py`.

2. Add the v1 dependencies declared in `spec/build-spec.md` "Core libraries":

   ```powershell
   uv add pydantic typer "jinja2>=3" ruamel.yaml python-frontmatter rich httpx
   uv add --dev pytest pytest-cov pytest-asyncio mypy ruff
   ```

3. Implement against `spec/build-spec.md` "Architecture layers" and "Acceptance Criteria". The first dogfood milestone is `swarmlord list` and `swarmlord render` working against the originating packet at `<your-side-projects-path>/projects/2026-05-sandcastle-like-agent-orchestration/`.

4. Wire the CLI entry point in `pyproject.toml`:

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

- The v1 implementation itself.
- Whether `pyproject.toml` script entry uses `swarmlord` or also exposes `swarm` as an alias (recommend both via `[project.scripts]`).
- The exact shape of the `tests_passing` predicate's sandboxed exec (V2-relevant).
- Any V3 multi-tenancy decisions.

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
