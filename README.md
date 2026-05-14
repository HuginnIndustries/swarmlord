# SwarmLord

[![CI](https://github.com/HuginnIndustries/swarmlord/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/HuginnIndustries/swarmlord/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/swarmlord.svg)](https://pypi.org/project/swarmlord/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)
[![Code style: ruff](https://img.shields.io/badge/ruff-enabled-261230.svg)](https://github.com/astral-sh/ruff)

> The single orchestrator that coordinates a swarm of agent-workers.

SwarmLord reads project packets, picks the next dispatchable work, renders prompts, runs agents in isolated workspaces, gates stage promotions, and ships finished projects out as standalone repos.

Domain: [swarmlord.dev](https://swarmlord.dev) (owned, planned customer-facing surface for the V3 SaaS phase).

## Status

V1 implemented and dogfooded; current release is **0.1.1**. Python 3.12 package, Typer CLI, Pydantic v2 schemas, Jinja2 strict templating, atomic packet writes, SQLite run history (readable via `swarmlord log <slug>`), and runner registry (manual / claude-code-interactive / sandcastle-docker). FastAPI server scaffold returns 501s, ready for V2. Tests, lint, format, and `mypy --strict` all pass; coverage gate at 80% with ~85% reported across 99 tests. Release notes in [`CHANGELOG.md`](CHANGELOG.md).

**New here?** Read [`GUIDE.md`](GUIDE.md) — a 10-minute walkthrough from install through extracting a packet end-to-end.

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

- [`GUIDE.md`](GUIDE.md) — 10-minute walkthrough for new users (install → first packet → lifecycle → extract → customizing gates → troubleshooting).
- [`AGENTS.md`](AGENTS.md) — primary entry point for agents working on the codebase. Setup steps and what's settled vs open.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, quality gates, PR conventions.
- [`SECURITY.md`](SECURITY.md) — how to report a vulnerability.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes in keepachangelog.com format.
- [`src/swarmlord/`](src/swarmlord) — the Python package. Library + Typer CLI.
- [`spec/`](spec) — the originating design history, in order: `idea.md`, `discovery.md`, `inspiration-review.md`, `build-spec.md`. Read in that order to follow the reasoning.
- [`templates/packet/`](templates/packet) — packet scaffolding the `swarmlord new` command copies when creating new packets. Repo-local templates take precedence over the bundled fallback in `src/swarmlord/_templates/packet/`.
- [`examples/`](examples) — runnable sample packet you can poke at (`cd examples && swarmlord list`).
- [`tests/`](tests) — unit + integration test suite (99 tests; ~85% coverage).
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

## Contributing

PRs welcome. For anything beyond a typo, please open an issue first to confirm scope. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup and quality gates, and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.

## License

[MIT](LICENSE) © James Sesler
