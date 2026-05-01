# PROJECT_NAME Agent Guide

This folder is a self-contained project packet. It captures a side-project idea, refines it into an agent-ready spec, and prepares it for extraction into a standalone repo.

## First Read For New Sessions

Read these files in order:

1. `GUIDE.md`
2. `workflow/status.yaml`
3. `workflow/pipeline.yaml`
4. The current phase file named in `workflow/status.yaml`
5. Any relevant `skills/*/SKILL.md`

Treat this folder as durable memory. Continue the existing workflow instead of inventing a new structure.

## Trust Boundaries

| Category | Files | Access |
| --- | --- | --- |
| Instructions | `GUIDE.md`, `workflow/pipeline.yaml`, `skills/*/SKILL.md` | Read first. Edit only to improve this packet's workflow. |
| Workflow state | `workflow/status.yaml` | Update after meaningful work. |
| Durable specs | `spec/*.md`, `README.md`, `EXTRACT.md` | Create and update as the project matures. |
| Handoff log | `THREAD_LOG.md` | Append short session summaries. |
| Scratch | `scratch/*` | Disposable notes. |

## Stage Behavior

- `idea`: preserve the user's raw idea and infer a useful direction.
- `discovery`: research, refine, compare options, and identify a practical MVP.
- `spec-ready`: write or finish `spec/build-spec.md`.
- `build-ready`: implementation can begin.
- `extracted`: this packet has been moved to a dedicated repo.
- `archived`: no active work planned.

## Session Protocol

When starting, identify the current stage and next action from `workflow/status.yaml`.

When finishing durable work:

1. Update the current spec file.
2. Update `workflow/status.yaml`.
3. Append a concise entry to `THREAD_LOG.md`.
4. If the project status changed, update the root `projects/INDEX.md`.
