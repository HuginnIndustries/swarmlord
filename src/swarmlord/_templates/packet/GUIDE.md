# Packet Guide

This is a self-contained project packet operated by SwarmLord.

## Layout

- `README.md` — what this project is.
- `workflow/status.yaml` — current state. Stage, phase, open questions, etc.
- `workflow/WORKFLOW.md` — Jinja2 prompt template + per-stage gate predicates.
- `spec/` — durable design documents (`idea.md`, `discovery.md`, `build-spec.md`).
- `skills/` — per-phase prompt fragments.
- `THREAD_LOG.md` — append-only handoff log between sessions.
- `EXTRACT.md` — checklist for extracting this packet to a standalone repo.

## How to work this packet

Read `workflow/status.yaml`, then read the spec file for the current phase, then perform the first item in `next_actions`. Update status atomically when done. Append a dated entry to `THREAD_LOG.md`.
