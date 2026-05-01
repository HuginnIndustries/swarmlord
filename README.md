# SwarmLord

> The single orchestrator that coordinates a swarm of agent-workers.

SwarmLord reads project packets, picks the next dispatchable work, renders prompts, runs agents in isolated workspaces, gates stage promotions, and ships finished projects out as standalone repos.

Domain: [swarmlord.dev](https://swarmlord.dev) (owned, planned customer-facing surface for the V3 SaaS phase).

## Status

`spec-ready`, awaiting v1 implementation. The build spec at [`spec/build-spec.md`](spec/build-spec.md) is implementation-ready — schemas, interfaces, acceptance criteria, and the test plan are settled.

## Roadmap

- **V1** — local CLI + Python library. Typer + Pydantic v2 + Jinja2 (strict) + ruamel.yaml + SQLite for run history. Sandcastle invoked as a subprocess. Manual and interactive Claude Code runners ship alongside Sandcastle Docker.
- **V2** — FastAPI server + arq worker queue + Postgres. Same core, hosted as a daemon.
- **V3** — SaaS multi-tenancy. Auth, per-tenant isolation, usage metering, admin UI. Customer-facing surface at [swarmlord.dev](https://swarmlord.dev).

## What this repo contains

- [`spec/`](spec) — the originating design history, in order: `idea.md`, `discovery.md`, `inspiration-review.md`, `build-spec.md`. Read in that order to follow the reasoning.
- [`templates/packet/`](templates/packet) — packet scaffolding the future `swarmlord new` command will copy when scaffolding new project packets.
- `GUIDE.md` — guide for agents working inside this codebase. (Currently inherited from the originating packet; will be rewritten as code-development guidance during v1.)
- `THREAD_LOG.md` — running session log; append handoff entries here.

## Implementation entry point for the next agent

1. Read [`GUIDE.md`](GUIDE.md) for the working conventions.
2. Read [`spec/build-spec.md`](spec/build-spec.md) for everything: outcome, user workflows, architecture layers, schemas, runner protocol, CLI surface, acceptance criteria, test plan, and V2/V3 outline.
3. Read [`spec/inspiration-review.md`](spec/inspiration-review.md) only if you want the trade-off reasoning behind the architecture.
4. Run `uv init --package` to scaffold `pyproject.toml` and `src/swarmlord/`.
5. Implement v1 per the build spec. Do not re-decide architecture or naming — those are settled.

## Origin

This project began as a packet titled "Sandcastle-like Agent Orchestration" inside a `side-projects` backlog repo. The originating packet still lives at `side-projects/projects/2026-05-sandcastle-like-agent-orchestration/` as the historical record of how the design evolved from "sandcastle-like" to a layered system that combines lessons from Sandcastle (sandbox/branch primitives), Symphony (`WORKFLOW.md` policy + state machine), Paperclip (heartbeats + governance + budgets), Hermes (pluggable memory seam), and Graphify (structural memory layer).

## Naming note

The project name is **SwarmLord**. The two halves of the name describe its function: `swarm` is the many parallel agent-workers running in their own sandboxes, and `lord` is the singular orchestrator that coordinates them.

The CLI binary is `swarmlord` (with `swarm` available as a shorter alias). The Python package is `swarmlord`. If `swarmlord` is taken on PyPI, the package falls back to `swarmlord-orchestrator` while the brand, repo, and CLI binary stay `swarmlord` — the domain is the source of brand truth, not PyPI.

## License

TBD at first release.
