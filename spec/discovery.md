# Discovery

> **Historical design record.** This file captures the design as it stood
> before implementation. It is kept for provenance, not as a live roadmap —
> where it describes hosted, server, or multi-tenant phases, those were
> dropped: SwarmLord shipped as a local single-user CLI and stays that way.
> `README.md` and `AGENTS.md` describe the project as it actually is.

## Goal

Define a practical orchestration workflow that can operate on this repo's project packets and move them from rough ideas to build-ready projects.

## Audience

- Primary: the user, who wants to capture ideas casually and let agents refine or build them later.
- Secondary: future LLM agents entering the repo without previous chat context.

## Success Criteria

- A runner can identify each project's stage and next action from durable files.
- Fuzzy ideas trigger discovery/refinement instead of premature implementation.
- Build-ready packets can be handed to an implementation agent without structural uncertainty.
- Extracted projects retain enough local skills and workflow context to stand alone.

## Constraints

- V1 should stay manual-friendly and plain Markdown/YAML.
- Packet specs should remain runner-agnostic.
- Sandcastle-style branch/worktree isolation can be added later.
- The system should preserve durable state across chat sessions.

## Options Considered

- Runner-agnostic packet workflow: keep this repo as structured Markdown/YAML and let any agent consume it.
- Sandcastle-specific runner: add `.sandcastle` scripts and prompts early.
- Full control plane: build queues, validation, and orchestration commands from the start.

## Recommended MVP

Start with a runner-agnostic packet system and lightweight conventions. Once several packets exist, add automation that can:

1. List projects and stages.
2. Select the next action from `workflow/status.yaml`.
3. Generate a runner prompt from the packet's current phase and local skills.
4. Record results back into the packet.

## Risks

- Too much process may make idea capture feel heavy.
- Too little structure may leave future agents guessing.
- Runner-specific assumptions could make the packets harder to reuse.
- Unattended build agents need a clear confidence threshold before they mutate project code.

## Open Questions

- Which runner should be automated first: Codex, Claude Code, Sandcastle, or a simple local script?
- Should the orchestrator be a project in this repo first, then extracted later?
- What validation should gate the transition from `spec-ready` to `build-ready`?

## Inspiration Review (2026-05-01 follow-up)

After reading the neighboring repos, the conclusion is that "sandcastle-like" is the right framing only for the execution layer. The orchestration layer has better answers in Symphony, Paperclip, OpenClaw, Hermes Agent, and Graphify. The full comparison and synthesis lives in `spec/inspiration-review.md`. Summary:

- Sandcastle is the right execution primitive: branch strategies, worktree isolation, sandbox providers, prompt expansion, completion signals, lifecycle hooks, session capture and resume.
- Symphony contributes the policy file shape (`WORKFLOW.md` with YAML front matter plus prompt body), live reload, the orchestration state machine, reconciliation, continuation turns, packet-local skills, and the `linear_graphql`-style controlled tool injection pattern.
- Paperclip contributes the heartbeat execution model, atomic task checkout, governance and approval gates, budget caps, adapter registry, and goal ancestry on tickets. Defer until a daemon exists.
- OpenClaw contributes the skills-folder layering, onboarding/doctor flows, and a useful trust-posture vocabulary.
- Hermes Agent contributes the closed learning loop, pluggable memory backends, subagent spawning, terminal backends with serverless persistence, and cron-style scheduling.
- Graphify is the right structural memory layer at three levels: repo-wide map, packet-local map, and (later) an MCP tool every runner gets.

## Recommended Direction (post-review)

Build the v1 in five layers and only ship the first three:

1. Packet model — already in place. Stay with plain Markdown and YAML, the existing stage taxonomy, `pipeline.yaml`, and `EXTRACT.md`.
2. Per-packet `WORKFLOW.md` — Symphony-shaped, optional, declares runner profile, prompt template body, hooks, agent limits, completion signal, and stage-promotion gates.
3. Runner profiles — Sandcastle Docker is the first concrete one, with Sandcastle templates (`simple-loop`, `sequential-reviewer`, `parallel-planner-with-review`) as the catalog of orchestration shapes. Manual and interactive Claude Code remain valid runners for `discovery` packets.
4. Daemon and control plane — deferred; lift Symphony's state machine and Paperclip's atomic checkout when the backlog warrants it.
5. Memory — graphify on the repo root, graphify inside any packet that imports source material, and graphify-as-MCP-tool inside the future daemon.

## Resolved Open Questions

- Which runner first? Runner-agnostic at the packet layer. First concrete runner is Sandcastle (Docker bind-mount) for `build-ready` packets, manual or interactive Claude Code for `discovery` packets. Codex daemon is in scope only after a daemon ships.
- Where does the orchestrator live? In this repo, as `projects/2026-05-sandcastle-like-agent-orchestration/`. Extract once a daemon is real.
- What gates `spec-ready` -> `build-ready`? `spec/build-spec.md` has filled Outcome, User Workflows, Implementation Direction, Interfaces and Data, Acceptance Criteria, and Test Plan; `workflow/status.yaml.open_questions` is empty; `EXTRACT.md` is resolved as either "stays in repo" or has explicit extraction targets.

## New Open Questions

- What is the smallest useful schema for `WORKFLOW.md` front matter such that idea/discovery packets do not need it but spec-ready/build-ready packets do?
- Should `WORKFLOW.md` live in `workflow/` next to `status.yaml` and `pipeline.yaml`, or at the packet root?
- Should the runner-agnostic prompt template language be Liquid (Symphony's choice) or plain `{{KEY}}` substitution (Sandcastle's choice)?
- What is the minimum viable "next packet" picker? A bash script that greps `workflow/status.yaml` for stage-and-next-action pairs is probably enough for v1.
- When is graphify worth running? Probably only after a packet has accumulated source material (papers, transcripts, screenshots) or when the repo as a whole crosses some threshold of packet count.
