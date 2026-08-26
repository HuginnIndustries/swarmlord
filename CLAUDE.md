# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

SwarmLord is a Python 3.12 / Typer CLI + library that orchestrates "project packets" — directories under `./projects/<slug>/` that hold markdown specs and a typed `workflow/status.yaml`. The CLI walks those packets, decides what's dispatchable, renders prompts, runs agents, and gates stage promotions.

This is **the implementation repo**, not a packet. Packets live in `projects/` and are operated on by the CLI. The originating design history is in `spec/` (read in order: `idea.md` → `discovery.md` → `inspiration-review.md` → `build-spec.md`).

## Required reading before nontrivial work

1. `AGENTS.md` — what's settled, what's open, working conventions.
2. `spec/build-spec.md` — the implementation contract. Architecture, schemas, runner protocol, CLI surface, acceptance criteria. **Do not relitigate locked-in choices.**
3. `THREAD_LOG.md` — running handoff log; the most recent entries say what last happened.

## Commands

```sh
uv sync --dev                                  # install deps including dev tools
make check                                     # all four gates at once
uv run pytest                                  # 98 tests, ~85% coverage; 80% gate
uv run pytest tests/test_service.py            # single file
uv run pytest tests/test_service.py::test_x    # single test
uv run pytest -k "promote"                     # by keyword
uv run ruff check
uv run ruff format --check                     # CI uses --check; drop it to fix
uv run mypy --strict src/swarmlord
uv run swarmlord --help                        # smoke
```

All four (ruff check, ruff format --check, mypy --strict, pytest --cov) must pass before merging. CI on `.github/workflows/ci.yml` runs the same four on Ubuntu / Python 3.12.

Coverage gate is 80% globally (`fail_under = 80` in `pyproject.toml`). `runners/claude_code.py` is omitted from coverage.

`pytest` runs with `filterwarnings = ["error", ...]` — any unhandled warning fails the test.

## Architecture in one screen

The package is layered top-to-bottom; each layer only imports from layers below it:

```
cli.py          Typer entry point — thin shell, parses args, formats output
service.py      Composes core/packets/templating/runners into user operations
                (new, next, promote, render, run, extract, log, validate, …)
runners/        Runner protocol + ManualRunner, ClaudeCodeInteractiveRunner,
                SandcastleDockerRunner, plus a RunnerRegistry the service uses
templating/     Jinja2 with StrictUndefined; user content is inserted as
                already-rendered strings, never re-evaluated by the engine
packets/        Disk I/O: discovery, reader, writer (atomic temp+rename),
                INDEX.md upserts, THREAD_LOG.md appends
memory/         graphify on-demand
storage/        SQLite run history at ~/.local/share/swarmlord/runs.db
                (POSIX) or %APPDATA%\swarmlord\runs.db (Windows)
core/           Domain primitives — Stage/Phase enums, transition table,
                Pydantic v2 models, predicate vocabulary, gate evaluator,
                typed errors
```

The CLI is intentionally thin so anything embedding SwarmLord as a library can call the same `service` functions without going through Typer.

### State machine

Stages: `idea → discovery → spec_ready → build_ready → extracted → archived`. Forward transitions are gated by typed predicates evaluated against the packet's `workflow/WORKFLOW.md` front matter. Backward transitions are always allowed but require `--reason`, which gets recorded in `THREAD_LOG.md`. `LEGAL_TRANSITIONS` in `core/stages.py` is the source of truth — every transition (forward or back) must appear there.

Phases (`idea | discovery | build_spec | extraction | memory`) describe work happening *inside* a stage. `MEMORY` is transient and re-entrable from any stage.

### Predicate vocabulary

Defined as a Pydantic discriminated union in `core/models.py` so a typo in `kind:` is a load-time error. Kinds: `file_exists`, `file_section_filled`, `yaml_field_empty`, `yaml_field_equals`, `extract_md_resolved`, `tests_passing`. All file-targeted predicates are **path-confined** to the packet directory — `..` and absolute paths are rejected.

An empty gate list (`promote_to_spec_ready: []`) in a packet's `WORKFLOW.md` is authoritative — it means *no gates*, not "use defaults." Defaults only apply when no `WORKFLOW.md` exists at all.

### Templates: repo-local vs bundled

`swarmlord new` prefers `templates/packet/` at the repo root when scaffolding; it falls back to the bundled `src/swarmlord/_templates/packet/` if the repo-local copy is missing. When changing scaffold output, edit `templates/packet/` for visible behavior and keep the bundled copy in sync so installed-from-PyPI users get the same result.

## Conventions that are easy to violate

- **Atomic writes only.** `packets/writer.py` writes status via temp-file-and-rename. Never write directly to `status.yaml` or append to `THREAD_LOG.md` mid-stream — go through the existing helpers.
- **StrictUndefined everywhere.** Template rendering treats any missing variable as an error. User-supplied content is inserted as already-rendered strings; the engine never re-evaluates it.
- **Pydantic models forbid extras.** `_StrictModel` sets `extra="forbid"` and `validate_assignment=True`. If a field is missing from a real-world packet, prefer adding it to the schema over loosening the config. `extracted_to`/`extracted_on` are precedent — they exist because old packets carried them.
- **`runners/claude_code.py` is excluded from coverage** — it shells out to a real binary CI can't run. Don't add unit tests that exercise the subprocess.
- **No server, no hosted phase.** SwarmLord is a local single-user CLI. Don't add an HTTP surface, auth, or tenancy — the FastAPI scaffold that once reserved those paths was deliberately removed.
- **Convert relative dates** before persisting anything user-visible: slugs and `status.yaml` use absolute `YYYY-MM-DD`.

## Locked-in choices (don't relitigate without explicit user direction)

Python 3.12 via `uv`; Pydantic v2; Jinja2 `StrictUndefined`; Typer; SQLite for run history; runners limited to manual / claude-code-interactive / sandcastle-docker; stages/phases as code-defined enums; gates as Pydantic predicates; Graphify on demand; local single-user scope with no server or hosted phase; brand and CLI name `swarmlord`.

## Finishing meaningful work

1. Update code + tests; make sure ruff/format/mypy/pytest all pass.
2. Append a short handoff entry to `THREAD_LOG.md`.
3. If a milestone lands, update `README.md` Status and `CHANGELOG.md`.
