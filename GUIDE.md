# SwarmLord Guide

A 10-minute walkthrough that takes you from "I cloned the repo" to "I shipped
a packet end-to-end." Read this front-to-back the first time. After that, the
section headers are a reference.

If you already understand the moving parts and just want the spec, read
[`spec/build-spec.md`](spec/build-spec.md) instead.

## What SwarmLord does

You keep a folder of project packets — one per idea you're chewing on. Each
packet is a directory with a few markdown files (idea, discovery, build-spec)
and a typed `workflow/status.yaml` that tracks where the work is. SwarmLord
walks that folder, knows which packets are dispatchable next, renders prompts
for an LLM agent to act on, and gates promotions between stages so a packet
can't move forward until specific conditions are met (the section is filled,
the open-questions list is empty, EXTRACT.md is resolved, etc.).

V1 is a local CLI plus a Python library. You drive it from your shell.

## 1. Install

You'll need [`uv`](https://docs.astral.sh/uv/) and Python 3.12. From the
swarmlord repo:

```powershell
uv tool install --editable .
swarmlord --version
```

`--editable` means changes to the source are picked up without reinstalling.
To work on the source, run `uv sync --dev` instead and use `uv run swarmlord`.

## 2. Your first packet

`cd` into whatever directory you want to use as your packets root. Anything
with a `projects/` subdirectory works. The CLI always looks at the current
working directory.

```powershell
mkdir my-projects-root
cd my-projects-root
swarmlord new my-thing --title "My Thing" --summary "A short pitch."
```

This creates `projects/2026-MM-my-thing/` with:

- `workflow/status.yaml` — the typed state file.
- `workflow/WORKFLOW.md` — the prompt template + gate predicates for this
  packet (front matter is YAML config, body is a Jinja2 template).
- `spec/idea.md`, `spec/discovery.md`, `spec/build-spec.md` — the durable
  design documents.
- `EXTRACT.md` — a checklist that has to pass before the packet can
  graduate to its own repo.
- `THREAD_LOG.md` — append-only handoff log.
- `skills/` — per-phase prompt fragments.

Open `workflow/status.yaml` in an editor. The fields are:

```yaml
project_name: My Thing
slug: 2026-MM-my-thing
stage: idea            # idea -> discovery -> spec_ready -> build_ready -> extracted -> archived
current_phase: idea    # idea | discovery | build_spec | extraction | memory
created: 2026-MM-DD
updated: 2026-MM-DD
summary: A short pitch.
next_actions:
  - Capture the raw idea in spec/idea.md.
open_questions: []     # things blocking progression
resolved_questions: [] # questions you've answered (kept for history)
phase_status:
  idea: in_progress
runner_profile: null   # null | manual | claude-code-interactive | sandcastle-docker
```

Schema-validate it any time:

```powershell
swarmlord validate 2026-MM-my-thing
```

## 3. The lifecycle in one screen

The mental model is six stages:

```
idea  →  discovery  →  spec_ready  →  build_ready  →  extracted  →  archived
```

Forward transitions go through gates (typed predicates that inspect packet
files). Backward transitions are always allowed if you pass `--reason`.

Here's the full loop, top to bottom:

```powershell
swarmlord list                                  # see what's there
swarmlord next                                  # what should I work on?
swarmlord render 2026-MM-my-thing               # produce a prompt for the current phase
swarmlord render 2026-MM-my-thing --clipboard   # ...and copy it to clipboard
# paste into Claude Code, edit spec/idea.md, save status.yaml updates
swarmlord promote 2026-MM-my-thing --to discovery
# now spec/discovery.md is the file to fill in
swarmlord render 2026-MM-my-thing               # render the discovery-phase prompt
# fill spec/discovery.md, then:
swarmlord promote 2026-MM-my-thing              # default: promote to next forward stage
```

The promote step will fail loudly the first time you try it without filling
out the spec — that's the gate working. You'll see:

```
gates failed:
  - spec/discovery.md '## Recommended Direction' is empty
```

Add a `## Recommended Direction` section with content (no `TBD`/`TODO`/`FIXME`),
make sure `open_questions` is empty in `status.yaml`, then re-run. When the
gate passes:

```
promoted 2026-MM-my-thing: discovery -> spec_ready
  ok spec/discovery.md '## Recommended Direction' is filled
  ok workflow/status.yaml::open_questions is empty
```

## 4. Running an agent

`render` produces the prompt; `run` does the same and dispatches it to a
runner. V1 ships three runner profiles:

- **manual** (default, safest) — copies the prompt to your clipboard or
  prints it to stdout. You paste it into Claude Code or Codex yourself.
- **claude-code-interactive** — spawns the `claude` CLI in the packet
  directory with the prompt as initial input. Requires `claude` on PATH.
- **sandcastle-docker** — generates `.sandcastle/main.ts` and runs
  Sandcastle as a subprocess. Requires `npx` and `tsx`. *Note: the
  Sandcastle TypeScript template ships with a `TODO(v1-smoke)` flag —
  it has not been verified end-to-end against a real Sandcastle install.*

```powershell
swarmlord run 2026-MM-my-thing                            # uses packet's runner_profile
swarmlord run 2026-MM-my-thing --runner manual            # force manual
swarmlord run 2026-MM-my-thing --runner manual --dry-run  # render only, don't dispatch
```

Every run is recorded in SQLite at `~\.local\share\swarmlord\runs.db`
(POSIX) or `%APPDATA%\swarmlord\runs.db` (Windows). Even if a runner
crashes, the failed record persists with the exception text.

## 5. Reading history

```powershell
swarmlord log 2026-MM-my-thing                            # last 20 runs
swarmlord log 2026-MM-my-thing --gates --transitions      # full audit
swarmlord log 2026-MM-my-thing --json | jq                # machine-readable
swarmlord log 2026-MM-my-thing --limit 5
```

Three tables come out: runs (when, runner, exit code, status, signal,
error), gate evaluations (each predicate's pass/fail per promotion attempt),
and stage transitions (from → to with reason).

## 6. When you're done — extracting

When a packet has reached `build_ready` and its `EXTRACT.md` checkboxes are
all resolved, graduate it to a standalone repo:

```powershell
swarmlord extract 2026-MM-my-thing --target ~\Documents\GitHub\my-thing
```

This copies `README.md`, `GUIDE.md`, `THREAD_LOG.md`, `EXTRACT.md`, `spec/`,
`workflow/`, and `skills/` into the target, runs `git init` there, marks the
source packet as `extracted`, and updates `projects/INDEX.md` with the
destination path. The original packet stays as a historical record.

If a packet isn't quite ready and you need to ship anyway:

```powershell
swarmlord extract 2026-MM-my-thing --target <path> --force
```

`--force` skips the stage and predicate gates. Use sparingly.

## 7. Customizing a packet's gates

Each packet's `workflow/WORKFLOW.md` has YAML front matter that controls
which gates run on each promotion. The default scaffold gives you sensible
predicates; replace them with whatever fits the packet.

```yaml
---
runner_profile: manual
phase: discovery
agent:
  max_turns: 5
  completion_signal: "<promise>COMPLETE</promise>"
gates:
  promote_to_spec_ready:
    - kind: file_section_filled
      path: spec/discovery.md
      section: "## Recommended Direction"
    - kind: yaml_field_empty
      path: workflow/status.yaml
      field: open_questions
  promote_to_build_ready:
    - kind: file_section_filled
      path: spec/build-spec.md
      section: "## Outcome"
    - kind: file_section_filled
      path: spec/build-spec.md
      section: "## Acceptance Criteria"
    - kind: tests_passing
      command: "pytest -q"
    - kind: extract_md_resolved
---

Your Jinja2 prompt template goes here.

You are continuing work on packet `{{ packet.slug }}`.
Stage: {{ packet.stage.value }}.
Phase: {{ packet.current_phase.value }}.

Open questions:
{% for q in packet.open_questions %}- {{ q }}
{% endfor %}
```

The predicate vocabulary (V1):

| Kind | What it checks |
|------|----------------|
| `file_exists` | A file at the given path exists. |
| `file_section_filled` | A markdown heading exists, has content, and contains no forbidden tokens (default: `TBD`, `TODO`, `FIXME`). |
| `yaml_field_empty` | A dotted-path field in a YAML file is null or empty. |
| `yaml_field_equals` | A dotted-path field equals a literal. |
| `extract_md_resolved` | Every `- [ ]` checkbox in `EXTRACT.md` is marked `[x]`, marked `[-]` (deferred), or has "deferred" / "n/a" in its suffix text. |
| `tests_passing` | A shell command exits 0 from the packet root. |

All file-targeted predicates are **path-confined** — `..` segments and
absolute paths can't escape the packet directory. The predicate union is a
Pydantic discriminator, so a typo in `kind:` is caught at load time.

If you declare an empty list (`promote_to_spec_ready: []`), that's
authoritative — it means *no gates for this transition*, not "use the
defaults." Defaults only apply when no `WORKFLOW.md` exists at all.

For the full type definitions, see `spec/build-spec.md` § Predicate
vocabulary.

## 8. Troubleshooting

**`swarmlord list` shows nothing but I have a packet folder.**
Run `swarmlord validate --all`. Packets that fail schema validation are
filtered out of `list` (they show up after the table as a yellow `invalid
<slug>: <error>` block). Fix the schema error, then re-run `list`.

**`swarmlord render <slug>` says "no packet found" but the folder exists.**
Same cause as above — the packet failed schema. The render error message
points you at `swarmlord validate <slug>` for the full error.

**A `swarmlord promote` succeeded but the on-disk state looks weird.**
The promote sequence writes `status.yaml`, then appends to `THREAD_LOG.md`,
then updates `projects/INDEX.md`. If the process was interrupted between
those steps, the on-disk packet may be inconsistent. Run:

```powershell
swarmlord repair <slug>
```

That re-reads `status.yaml` through the schema and rewrites it canonically.

**Old packets that pre-date the current schema fail to validate.**
The schema was designed for forward compatibility — `extracted_to` and
`extracted_on` are accepted, and non-string items in the list fields are
coerced to strings. If you hit a different `extra_forbidden` error, the
field probably has to be added to the schema; file an issue or patch
`PacketStatus` in `core/models.py`.

**The slug column wraps awkwardly in a narrow terminal.**
That's `Rich` folding to keep the slug readable. The full slug is always
recoverable line-by-line; it never gets truncated with `…`. Widen the
terminal or use `swarmlord list --json` for clean output.

## Where to go next

- [`spec/build-spec.md`](spec/build-spec.md) — the implementation contract.
  Read this if you want the full type system, the runner protocol, the V2/V3
  outline, or the test plan.
- [`AGENTS.md`](AGENTS.md) — onboarding doc for someone (or some agent)
  working on the swarmlord codebase itself. Read this if you want to
  contribute, not just use.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes.
- [`THREAD_LOG.md`](THREAD_LOG.md) — running session log of decisions.
