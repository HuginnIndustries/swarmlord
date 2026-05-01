# SwarmLord

> The single orchestrator that coordinates a swarm of agent-workers.

SwarmLord reads project packets, picks the next dispatchable work, renders prompts, runs agents in isolated workspaces, gates stage promotions, and ships finished projects out as standalone repos.

Domain: [swarmlord.dev](https://swarmlord.dev) (owned, planned customer-facing surface for the V3 SaaS phase).

## Status

V1 implemented and dogfooded; current release is **0.1.1**. Python 3.12 package, Typer CLI, Pydantic v2 schemas, Jinja2 strict templating, atomic packet writes, SQLite run history (readable via `swarmlord log <slug>`), and runner registry (manual / claude-code-interactive / sandcastle-docker). FastAPI server scaffold returns 501s, ready for V2. Tests, lint, format, and `mypy --strict` all pass; coverage gate at 80% with ~85% reported across 99 tests. Release notes in [`CHANGELOG.md`](CHANGELOG.md).

```powershell
# Install (editable)
cd ~\Documents\GitHub\swarmlord
uv sync --dev

# Smoke
uv run swarmlord --help
uv run swarmlord list
uv run swarmlord new sample-packet --title "Sample" --summary "A sample packet"
uv run swarmlord render sample-packet
uv run swarmlord promote sample-packet --to discovery
```

## Roadmap

- **V1** — local CLI + Python library. Typer + Pydantic v2 + Jinja2 (strict) + ruamel.yaml + SQLite for run history. Sandcastle invoked as a subprocess. Manual and interactive Claude Code runners ship alongside Sandcastle Docker.
- **V2** — FastAPI server + arq worker queue + Postgres. Same core, hosted as a daemon.
- **V3** — SaaS multi-tenancy. Auth, per-tenant isolation, usage metering, admin UI. Customer-facing surface at [swarmlord.dev](https://swarmlord.dev).

## What this repo contains

- [`AGENTS.md`](AGENTS.md) — primary entry point for agents working on the codebase. Setup steps and what's settled vs open.
- [`src/swarmlord/`](src/swarmlord) — the Python package. Library + Typer CLI.
- [`spec/`](spec) — the originating design history, in order: `idea.md`, `discovery.md`, `inspiration-review.md`, `build-spec.md`. Read in that order to follow the reasoning.
- [`templates/packet/`](templates/packet) — packet scaffolding the `swarmlord new` command copies when creating new packets. Repo-local templates take precedence over the bundled fallback in `src/swarmlord/_templates/packet/`.
- [`tests/`](tests) — unit + integration test suite (99 tests; ~85% coverage).
- [`CHANGELOG.md`](CHANGELOG.md) — release notes in keepachangelog.com format.
- `GUIDE.md` — packet-progression content carried from the originating packet.
- `THREAD_LOG.md` — running session log; append handoff entries here.

## V1 CLI surface

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
swarmlord serve     # V2 stub — exits 2
```

## Implementation entry point for the next agent

1. Read [`AGENTS.md`](AGENTS.md) — Setup steps, what's settled, and working conventions.
2. Read [`spec/build-spec.md`](spec/build-spec.md) — everything: outcome, user workflows, architecture layers, schemas, runner protocol, CLI surface, acceptance criteria, test plan, and V2/V3 outline.
3. Read [`spec/inspiration-review.md`](spec/inspiration-review.md) only if you want the trade-off reasoning behind the architecture.
4. Implement v1 per the build spec. Do not re-decide architecture or naming — those are settled.

## Origin

This project began as a packet titled "Sandcastle-like Agent Orchestration" inside a `side-projects` backlog repo. The originating packet still lives at `side-projects/projects/2026-05-sandcastle-like-agent-orchestration/` as the historical record of how the design evolved from "sandcastle-like" to a layered system that combines lessons from Sandcastle (sandbox/branch primitives), Symphony (`WORKFLOW.md` policy + state machine), Paperclip (heartbeats + governance + budgets), Hermes (pluggable memory seam), and Graphify (structural memory layer).

## Naming note

The project name is **SwarmLord**. The two halves of the name describe its function: `swarm` is the many parallel agent-workers running in their own sandboxes, and `lord` is the singular orchestrator that coordinates them.

The CLI binary is `swarmlord` (with `swarm` available as a shorter alias). The Python package is `swarmlord`. If `swarmlord` is taken on PyPI, the package falls back to `swarmlord-orchestrator` while the brand, repo, and CLI binary stay `swarmlord` — the domain is the source of brand truth, not PyPI.

## License

TBD at first release.
