# SwarmLord

[![CI](https://github.com/HuginnIndustries/swarmlord/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/HuginnIndustries/swarmlord/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)
[![Code style: ruff](https://img.shields.io/badge/ruff-enabled-261230.svg)](https://github.com/astral-sh/ruff)

**A CLI that keeps a backlog of software projects moving through a typed state machine, and hands each step to a coding agent with the right prompt.**

Agent tooling is good at doing one task and bad at knowing which task is next. SwarmLord fills that gap. You keep your projects on disk as *packets* — a directory of markdown specs plus a typed `workflow/status.yaml`. SwarmLord reads them, tells you which one is ready for work, renders the prompt for that specific stage, dispatches it to a runner, and refuses to advance a project past a stage until machine-checkable conditions are actually met.

The interesting part isn't the agent invocation. It's that **"is this project ready for the next stage?" is a typed predicate evaluated against files on disk**, not a judgment call.

```
idea → discovery → spec_ready → build_ready → extracted → archived
        └── each arrow is guarded by gates that must evaluate true
```

![A terminal session: creating a packet, listing the backlog, asking what to work on, promoting through two stages with their gates passing, then a third promotion refused because EXTRACT.md still has unresolved checkboxes — exiting 2.](docs/demo.svg)

<sup>Real output, not a mock-up — regenerate it any time with `uv run python scripts/make_demo_svg.py`.</sup>

## Try it in two minutes

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```sh
uv tool install git+https://github.com/HuginnIndustries/swarmlord

mkdir my-backlog && cd my-backlog
swarmlord new csv-linter --title "CSV Linter" \
  --summary "Catch malformed rows before they hit the warehouse"

swarmlord list     # the backlog, with each packet's stage
swarmlord next     # what to work on, and the next concrete action
```

The part worth pausing on is what happens when a promotion hasn't earned it:

```sh
$ swarmlord promote 2026-08-csv-linter --to build_ready
gates failed:
  - EXTRACT.md has 10 unresolved checkbox(es); first: line 7:
    - [ ] `spec/build-spec.md` is complete enough for implementation.
$ echo $?
2
```

That exit code matters: promotions are scriptable and CI-checkable, because the gate result is data rather than prose.

New here? [`GUIDE.md`](GUIDE.md) is a 10-minute walkthrough from install through extracting a finished packet into its own repo.

## How it works

**Packets.** A packet is `./projects/<YYYY-MM-slug>/` holding `spec/` markdown, an `EXTRACT.md` shipping checklist, a `THREAD_LOG.md`, and `workflow/status.yaml` — the typed state. Nothing is hidden in a database; the directory *is* the project, and it stays readable and diffable in git.

**Stages and phases.** Stages (`idea → discovery → spec_ready → build_ready → extracted → archived`) track how far along a project is. Phases (`idea`, `discovery`, `build_spec`, `extraction`, `memory`) describe the work happening inside a stage. Both are code-defined enums, and `LEGAL_TRANSITIONS` in `core/stages.py` is the single source of truth — a transition that isn't in that table cannot happen. Backward transitions are always allowed but require `--reason`, which gets written into the packet's `THREAD_LOG.md`.

**Gates.** Each forward transition is guarded by predicates declared in the packet's own `workflow/WORKFLOW.md` front matter:

```yaml
gates:
  promote_to_spec_ready:
    - kind: file_section_filled
      path: spec/discovery.md
      section: "## Recommended Direction"
    - kind: yaml_field_empty
      path: workflow/status.yaml
      field: open_questions
```

The predicate vocabulary (`file_exists`, `file_section_filled`, `yaml_field_empty`, `yaml_field_equals`, `extract_md_resolved`, `tests_passing`) is a Pydantic v2 discriminated union, so a typo in `kind:` is a load-time error rather than a gate that silently never fires. Every file-targeted predicate is path-confined to the packet directory — `..` and absolute paths are rejected.

**Prompts.** Rendered with Jinja2 under `StrictUndefined`, so a missing template variable is an error instead of a silently empty prompt. User content is inserted as already-rendered strings; the engine never re-evaluates packet data as a template.

**Runners.** A small `Runner` protocol with three implementations: `manual` (render the prompt, copy it, paste it wherever you like), `claude-code-interactive` (hand off to the Claude Code CLI), and `sandcastle-docker` (dispatch into a container). Every dispatch is recorded in a local SQLite run history you can read back with `swarmlord log <slug>`.

## Architecture

Layered top-to-bottom; each layer imports only from layers below it.

```
cli.py          Typer entry point — parses args, formats output, nothing else
service.py      Composes the layers below into user operations
runners/        Runner protocol + manual / claude-code / sandcastle + registry
templating/     Jinja2 with StrictUndefined
packets/        Disk I/O: discovery, reader, atomic writer, INDEX/THREAD_LOG
memory/         Graphify integration, invoked on demand
storage/        SQLite run history in the platform data dir
core/           Stage/Phase enums, transition table, Pydantic models,
                predicate vocabulary, gate evaluator, typed errors
```

Two rules hold that structure together. Writes to `status.yaml` go through `packets/writer.py`, which uses temp-file-and-rename so an interrupted run can't leave a half-written state file — and `swarmlord repair` re-derives consistent state if one ever does. And the CLI stays thin, so the service functions are usable as a library without going through Typer.

## Engineering standards

Four gates run on every push ([`ci.yml`](.github/workflows/ci.yml), Ubuntu / Python 3.12) and must pass before merge:

| Gate | Command | State |
| --- | --- | --- |
| Lint | `uv run ruff check` | clean |
| Format | `uv run ruff format --check` | clean |
| Types | `uv run mypy --strict src/swarmlord` | clean, 29 source files, no `Any` escapes |
| Tests | `uv run pytest --cov` | 98 tests, ~85% coverage, gate at 80% |

`make check` runs all four. `pytest` is configured with `filterwarnings = ["error"]`, so an unhandled warning fails the suite.

## Command surface

```
swarmlord list [--stage X] [--phase Y] [--json]
swarmlord next [--stage X] [--runner-profile P]
swarmlord new <slug> [--title TITLE] [--summary TEXT] [--runner-profile P]
swarmlord render <slug> [--phase Y] [--attempt N] [--clipboard]
swarmlord run <slug> [--runner PROFILE] [--dry-run]
swarmlord promote <slug> [--to STAGE] [--reason REASON] [--demote]
swarmlord validate <slug | --all>
swarmlord graphify <slug | --repo> [--update]
swarmlord extract <slug> --target PATH [--no-git] [--force]
swarmlord log <slug> [--limit N] [--gates] [--transitions] [--json]
swarmlord repair <slug>
```

`--json` on `list` and `log` emits machine-readable output for scripting.

## Repository map

- [`GUIDE.md`](GUIDE.md) — 10-minute walkthrough: install → first packet → lifecycle → extract → custom gates → troubleshooting.
- [`src/swarmlord/`](src/swarmlord) — the package. Library plus Typer CLI.
- [`tests/`](tests) — unit and integration suite.
- [`templates/packet/`](templates/packet) — scaffolding `swarmlord new` copies. Repo-local templates take precedence over the bundled fallback in `src/swarmlord/_templates/packet/`.
- [`examples/`](examples) — a runnable sample packet (`cd examples && swarmlord list`).
- [`scripts/make_demo_svg.py`](scripts/make_demo_svg.py) — regenerates the demo above by running the CLI for real and rendering the session to SVG.
- [`skills/`](skills) — an operator skill that lets an agent drive the CLI from natural language.
- [`spec/`](spec) — the original design record, kept as history: `idea.md` → `discovery.md` → `inspiration-review.md` → `build-spec.md`.
- [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), [`CHANGELOG.md`](CHANGELOG.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Scope

SwarmLord is a local, single-user tool, and that's the whole design. There is no hosted service, no server component, and no multi-tenancy — state lives in a directory you own and a SQLite file on your machine. Ideas that would push it toward being a platform are out of scope; ideas that make the local tool sharper are welcome.

## Origin

SwarmLord started as one entry in a personal side-project backlog — a packet describing an agent orchestrator — and became the tool that now operates that backlog. The design record in [`spec/`](spec) traces how it got there, drawing on Sandcastle (sandbox and branch primitives), Symphony (`WORKFLOW.md` policy plus a state machine), Paperclip (heartbeats, governance, budgets), Hermes (a pluggable memory seam), and Graphify (structural memory).

The name splits the way the system does: *swarm* is the parallel agent-workers, *lord* is the one process that decides what they work on.

## Contributing

Contributions welcome. For anything beyond a typo, open an issue first so we can agree on scope. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers dev setup and the quality gates; [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) covers community expectations.

## License

[MIT](LICENSE) © James Sesler
