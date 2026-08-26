# Inspiration Review

> **Historical design record.** This file captures the design as it stood
> before implementation. It is kept for provenance, not as a live roadmap —
> where it describes hosted, server, or multi-tenant phases, those were
> dropped: SwarmLord shipped as a local single-user CLI and stays that way.
> `README.md` and `AGENTS.md` describe the project as it actually is.

Durable notes on the repos that should inform this packet's build spec. The packet itself was originally framed as "a sandcastle-like" system, but a fair review of the neighboring repos shows the right v1 sits across several of them, not just sandcastle. This file captures what each repo does best, what to borrow, and what to leave out.

Every repo referenced here was a local checkout on the author's machine. None of these are edited from this packet; they are read-only inspiration.

## Sandcastle (TypeScript library)

Role: a programmatic primitive for "run this prompt against this repo in an isolated sandbox and get back commits."

Strengths to borrow:

- Branch strategies (`head` / `merge-to-head` / `branch`) layered on git worktrees so commits land somewhere safe by default.
- Sandbox provider abstraction (Docker, Podman, Vercel, custom bind-mount or isolated). The provider contract is small enough to copy.
- Per-run prompt file (`.sandcastle/prompt.md`) with three nice features: `` !`shell-command` `` expansion, `{{ARG}}` substitution from `promptArgs`, and built-in `{{SOURCE_BRANCH}}` / `{{TARGET_BRANCH}}` injection.
- `<promise>COMPLETE</promise>` early-termination convention.
- Lifecycle hooks split by location: `host.onWorktreeReady`, `host.onSandboxReady`, `sandbox.onSandboxReady`.
- Session capture and resume (`claudeCode --resume <id>`).
- Templates as a catalog of orchestration shapes: `simple-loop`, `sequential-reviewer`, `parallel-planner`, `parallel-planner-with-review`.

Limitations: single repo, single ticket source, single agent perspective. No backlog model, no daemon, no policy file. Sandcastle is the execution layer; it does not answer "which packet do we work on next" or "is this packet ready for a build agent."

## Symphony (OpenAI, Elixir reference impl plus a language-agnostic SPEC.md)

Role: a long-running daemon that polls an issue tracker (Linear), claims tickets, runs Codex app-server in per-issue workspaces, retries with backoff, reconciles tracker state. The orchestration layer above the per-run primitive.

Strengths to borrow:

- `WORKFLOW.md` as a single repo-owned policy file. YAML front matter declares tracker, polling, workspace root, hooks (`after_create`, `before_run`, `after_run`, `before_remove`), agent limits, codex settings; the markdown body is the per-issue prompt template. Policy and prompt are versioned with the code.
- Live reload of `WORKFLOW.md` without restart. New cadence, concurrency, hooks, and prompts apply to future runs.
- Explicit state machine: `Unclaimed`, `Claimed`, `Running`, `RetryQueued`, `Released`, plus a separate run-attempt phase enum (`PreparingWorkspace`, `BuildingPrompt`, `LaunchingAgentProcess`, `InitializingSession`, `StreamingTurn`, `Finishing`, `Succeeded`, `Failed`, `TimedOut`, `Stalled`, `CanceledByReconciliation`).
- Reconciliation every tick: stall detection by event inactivity, tracker state refresh, startup terminal cleanup of stale workspaces.
- Per-issue persistent workspaces reused across runs, keyed by sanitized identifier.
- Continuation turns inside the same coding-agent thread up to `agent.max_turns`, with the first turn rendering the full prompt and later turns sending only continuation guidance.
- Skills folder (`.codex/skills/<name>/SKILL.md`) for repeated sub-flows like `linear`, `commit`, `pull`, `push`, `land`.
- `linear_graphql` extension: a single client-side tool exposed to the agent that reuses Symphony's tracker auth so the agent never reads raw tokens.
- Per-state concurrency caps via `agent.max_concurrent_agents_by_state`.
- Backoff formula: `delay = min(10000 * 2^(attempt - 1), agent.max_retry_backoff_ms)`, plus a one-second continuation retry after clean exits.

Limitations: Linear-bound for v1, daemon model assumes a tracker as the source of truth, heavier than what a side-projects backlog needs to start, ticket writes happen through the agent rather than the orchestrator.

## Paperclip (Node/React multi-agent control plane)

Role: a "company" layer with org chart, budgets, governance, heartbeats, scheduled routines, ticket system, plugins. Uses agents like OpenClaw, Claude Code, Codex as workers.

Strengths to borrow:

- Heartbeat execution: scheduled wakeups with budget checks, workspace resolution, secret injection, skill loading, adapter invocation, structured logs, cost events, audit trails, and recovery for orphaned runs.
- Atomic task checkout with execution locks so two agents cannot pick up the same ticket.
- Adapter registry that treats Claude Code, Codex, CLI tools, and HTTP webhook bots uniformly.
- Goal ancestry on tickets so agents always see the "why" not just the title.
- Governance: approval gates with rollback, agent pause/resume/terminate, budget hard-stops.
- Company portability: export and import entire orgs (agents, skills, projects, routines) with secret scrubbing.
- Plugins as out-of-process workers behind capability-gated host services.

Limitations: heavy infra (Node server, embedded Postgres, React UI), opinionated multi-tenant company model, more than this repo needs in v1.

## OpenClaw (personal AI assistant gateway)

Role: a local-first personal assistant with messaging gateways, sessions, skills, voice, canvas.

Strengths to borrow:

- Skills folder layering: bundled, managed, and workspace-level skills, all `.agents/skills/<name>/SKILL.md`.
- Multi-agent routing per channel and isolated workspaces per agent.
- Sessions with isolation, activation modes, queue modes, reply-back.
- `openclaw onboard` and `openclaw doctor` flows. Onboarding for guided setup; doctor for config validation. Both are good models for a future side-projects CLI that scaffolds a packet or audits packet health.
- Trust posture: inbound DMs are untrusted by default and require pairing. Useful framing for "what is the trust level of this packet right now."

## Hermes Agent (Nous Research, self-improving agent runtime)

Role: terminal/messaging agent with a closed learning loop, persistent memory, scheduled cron, subagent delegation, and many terminal backends.

Strengths to borrow:

- Closed learning loop: agent-curated memory with periodic nudges, autonomous skill creation after complex tasks, skills that self-improve during use, FTS5 session search with LLM summarization for cross-session recall, dialectic user modeling. Compatible with the agentskills.io standard.
- Plugin memory layer with multiple backends (mem0, supermemory, holographic, openviking, retaindb, byterover, hindsight, honcho). Treat memory as a pluggable seam, not one fixed backend.
- Subagent spawning for parallel workstreams with isolated context.
- Terminal backends: local, Docker, SSH, Daytona, Singularity, Modal — including serverless persistence (hibernates when idle, wakes on demand).
- Cron-based scheduled automations with platform delivery.

Limitations: ships its own runtime, opinionated about TUI and messaging gateways; we want a thinner orchestration layer that drives existing runtimes.

## Graphify (knowledge-graph skill)

Role: a multi-platform skill that turns any folder of files into a NetworkX knowledge graph. Outputs `graph.json`, `GRAPH_REPORT.md`, `graph.html`, plus an MCP server.

Strengths to borrow:

- Persistent, cacheable, queryable representation of "everything in this folder" without an embedding store. Code goes through tree-sitter AST locally (no LLM); docs/papers/images/audio/video go through Claude or Codex extraction. Cluster via Leiden community detection on the topology directly.
- Edge labels: `EXTRACTED` (1.0 confidence), `INFERRED` (with score), `AMBIGUOUS` (flagged). Honest about found vs guessed.
- Always-on PreToolUse hooks (Claude Code, Codex, OpenCode, Gemini) that remind the assistant to read `GRAPH_REPORT.md` before grepping. Cursor/Kiro/Antigravity equivalents via rules files.
- Git post-commit and post-checkout hooks to rebuild the graph automatically.
- MCP server (`python -m graphify.serve graph.json`) exposing `query_graph`, `get_node`, `get_neighbors`, `shortest_path`.
- Wiki output (`--wiki`) for runners that prefer markdown navigation over JSON.
- Cross-repo merge: combine multiple `graph.json` files into a portfolio-wide map.

# What to combine for this packet

The packet asked for "a sandcastle-like" system. The fair conclusion after reading the neighbors is that the right v1 is a small layered system, with each layer borrowing from a different repo.

## Layer 1 — Packet model (already in place)

Stay with the current plain-Markdown/YAML packet:

- `projects/<slug>/spec/*.md` for durable specs.
- `projects/<slug>/workflow/{status.yaml,pipeline.yaml}` for workflow state.
- `projects/<slug>/skills/<name>/SKILL.md` for packet-local skills.
- `projects/<slug>/THREAD_LOG.md` for handoff entries.
- `projects/INDEX.md` at repo root.

This already mirrors paperclip's "tasks carry full goal ancestry," symphony's "policy in-repo," and the Anthropic skills convention shared by openclaw, hermes, and graphify. Keep the stage taxonomy (`idea` -> `discovery` -> `spec-ready` -> `build-ready` -> `extracted` -> `archived`), `pipeline.yaml` phase definitions, and `EXTRACT.md` checklist.

## Layer 2 — Per-packet `WORKFLOW.md` (Symphony-style policy file, optional)

Add an optional `workflow/WORKFLOW.md` per packet with YAML front matter that declares:

- `runner_profile`: which runner family applies (e.g. `manual`, `claude-code-interactive`, `sandcastle-docker`, `sandcastle-vercel`, `codex-daemon`).
- `phase`: which phase the packet is currently in (mirrors `status.yaml.current_phase`; this file remains the source of truth for the prompt).
- `prompt_template`: the markdown body, rendered with packet-level variables (`{{ packet }}`, `{{ stage }}`, `{{ open_questions }}`, etc.).
- `hooks`: `after_create`, `before_run`, `after_run`, `before_remove` (Symphony shape).
- `agent`: `max_turns`, `stall_timeout_ms`, `max_retry_backoff_ms`, `completion_signal` (default `<promise>COMPLETE</promise>` per Sandcastle).
- `gates`: a list of "must be true before promoting to the next stage" predicates (filled-in spec sections, empty open questions, presence of `EXTRACT.md` content).

Keep it declarative so any runner — Sandcastle, raw Codex CLI, Claude Code interactive, or a Python script — can consume it. `idea` and `discovery` packets do not need a `WORKFLOW.md` until they reach `spec-ready` or `build-ready`.

## Layer 3 — Runner profiles (Sandcastle as the first concrete one)

Use Sandcastle as the execution primitive when implementation is needed:

- `discovery` agents: interactive, no sandbox (`wt.interactive()` with `noSandbox()`).
- `build` agents: sandboxed, branch strategy `branch` or `merge-to-head`, completion signal `<promise>COMPLETE</promise>`, session capture on so the next session can resume with `--resume`.
- `review` agents: `createSandbox()` + multiple `sandbox.run()` calls so the reviewer sees the same container/branch the implementer left.

Borrow Sandcastle's templates as the catalog of orchestration shapes (`simple-loop`, `sequential-reviewer`, `parallel-planner-with-review`). Each template becomes a runner profile a `WORKFLOW.md` can reference by name.

## Layer 4 — Daemon and control plane (defer; lift Symphony + Paperclip when needed)

Do not build this in v1. When the backlog grows, add a small reader/runner that:

1. Enumerates packets under `projects/`.
2. Picks the next dispatchable packet from `status.yaml.stage` and `next_actions` (the local filesystem is the "tracker").
3. Builds a runner prompt from the packet's `WORKFLOW.md`, current phase, and packet-local skills.
4. Invokes the chosen runner.
5. Writes results back into `status.yaml`, `THREAD_LOG.md`, and the relevant `spec/*.md` (the way Symphony agents update tickets via tooling).

When the daemon matures, lift Symphony's state machine, exponential backoff, reconciliation, and continuation-turn behavior. Lift Paperclip's atomic checkout, budget caps, governance gates, and heartbeat scheduling. Hermes's cron-style scheduled runs are the natural extension.

## Layer 5 — Memory (Graphify in three places)

Graphify is the right structural-memory layer for this stack. Three integration points:

1. Repo-level memory of the entire side-projects backlog. Run graphify on the repo root. `graphify-out/GRAPH_REPORT.md` becomes the entry-point map any agent reads when starting a session. `graph.json` exposed via `python -m graphify.serve` gives every runner an MCP tool to query "what packets touch concept X", "what depends on what", "what extraction is recent" without grepping every packet. Install always-on hooks (`graphify claude install`, `graphify codex install`) so any agent navigates by graph first. Commit `graphify-out/` minus `cache/`, `manifest.json`, and `cost.json`.

2. Packet-level memory for packets that import a lot of source material (research notes, papers, screenshots, recordings, scraped competitor specs). Run graphify inside the packet folder; `projects/<slug>/graphify-out/` becomes packet-local semantic memory. Discovery agents read its `GRAPH_REPORT.md` before re-extracting. When the packet matures into a build-ready spec, the graph travels with the extracted repo because graphify is per-folder.

3. Memory inside the future agentic orchestration system. When the daemon ships, inject graphify the way Symphony injects `linear_graphql`: as a controlled MCP tool every runner gets (`query_graph`, `get_node`, `get_neighbors`, `shortest_path`). Cheaper than passing the whole repo into every prompt and forces agents to converge on shared terminology. Hermes's pluggable memory backends suggest leaving room for a separate conversational-memory plugin alongside graphify; do not ship one yet, but mark the seam.

# Concrete next actions for this packet

These should land in `spec/discovery.md` and `workflow/status.yaml` so the packet becomes ready to write a build spec:

1. Pick the v1 runner profile: runner-agnostic packets at the policy layer; first concrete runner is Sandcastle (Docker bind-mount) for build-ready packets and manual or interactive Claude Code for discovery packets. Codex daemon is deferred until a daemon exists.
2. Resolve the open question on where the orchestrator lives: start in this repo as `projects/2026-05-sandcastle-like-agent-orchestration/`. Extract once a daemon ships.
3. Resolve the unattended-build confidence question: a packet is unattended-build-ready when `spec/build-spec.md` has filled `Outcome`, `User Workflows`, `Implementation Direction`, `Interfaces and Data`, `Acceptance Criteria`, and `Test Plan`; `workflow/status.yaml.open_questions` is empty; `EXTRACT.md` is either resolved as "stays in repo" or has explicit extraction targets.
4. Add a `WORKFLOW.md` template under `templates/project-packet/workflow/WORKFLOW.md` capturing the Symphony-shaped front matter from Layer 2. Mark it optional for `idea` and `discovery` packets.
5. Add a graphify integration plan to the build spec covering the three layers above. Include the `.gitignore` additions graphify recommends.
6. Update `pipeline.yaml` to call out a `memory` concern in `idea` and `discovery` so big-corpus packets get a graph automatically when source material is dropped in.

# What to leave out of v1

- A daemon, scheduler, or polling loop. Premature.
- A bring-your-own-tracker abstraction. Filesystem packets are the tracker for now.
- A web UI or React dashboard. The repo is the UI.
- A budget/cost ledger. Add when costs become real, lifting from Paperclip.
- Self-improving skills (Hermes-style). Add once enough packets have run that the patterns stabilize.
- Multi-tenant company portability (Paperclip-style). Single user, single repo for now.
