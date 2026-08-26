# Skill: SwarmLord Operator

You are operating SwarmLord — a CLI orchestrator for project packets — on
behalf of a user who is talking to you in natural language. Your job is to
translate their intent into the right `swarmlord` commands, read the
structured output back, and report results in plain language.

This skill is the operator's manual. Read it once, then drive.

---

## When this skill applies

The user says any of:

- "let's start a project on X" → `swarmlord new`
- "what should I work on?" / "what's next?" → `swarmlord next`
- "show me what packets I have" / "list" → `swarmlord list`
- "give me the prompt for X" / "render X" → `swarmlord render`
- "move X forward" / "promote X" → `swarmlord promote`
- "what happened with X?" / "show history" → `swarmlord log`
- "ship X" / "extract X" → `swarmlord extract`

If the user asks about something orthogonal to packet operations (general
coding help, unrelated questions), don't invoke swarmlord; just answer.

## Mental model in one screen

A **packet** is a directory under `./projects/<slug>/` containing markdown
specs, a `workflow/status.yaml` (the typed state), an optional
`workflow/WORKFLOW.md` (Jinja prompt template + gate config), and skills.
Packets move through six **stages**:

```
idea → discovery → spec_ready → build_ready → extracted → archived
```

Each forward transition runs **gate predicates** that inspect the packet's
files. The transition is refused if any predicate fails. Backward
transitions are always allowed if the user provides a `--reason`.

Within a stage, work happens in **phases** (`idea`, `discovery`,
`build_spec`, `extraction`). The phase is what you render a prompt against;
the stage is the durable lifecycle marker.

## Always start with `swarmlord list`

Before doing anything else in a session, run:

```
swarmlord list --json
```

That tells you what packets exist, what stage each is in, and which (if
any) failed schema validation. If a packet you need to operate on shows up
as `invalid`, run `swarmlord validate <slug>` to see why before touching
it.

## Command surface

All commands accept `--help`. Run from the user's packets root (the
directory containing `./projects/`).

| Command | Purpose | Idempotent? | JSON? |
|---|---|---|---|
| `list [--stage X] [--phase Y] [--json]` | enumerate packets | yes | yes |
| `next [--stage X] [--runner-profile P]` | top dispatchable packet | yes | no |
| `new <slug> [--title T] [--summary S] [--runner-profile P]` | scaffold a new packet | no — creates files | no |
| `render <slug> [--phase P] [--attempt N] [--clipboard]` | print the prompt for the packet's current phase | yes | no (raw text) |
| `run <slug> [--runner P] [--attempt N] [--dry-run]` | render and dispatch to a runner | depends on runner | no |
| `promote <slug> [--to STAGE] [--reason R] [--demote]` | run gates, transition stage | no — writes status / log / index | no |
| `validate <slug | --all>` | schema-validate packet(s) | yes | no |
| `graphify <slug | --repo> [--update]` | run graphify subprocess | depends | no |
| `extract <slug> --target PATH [--no-git] [--force]` | graduate to standalone repo | no — copies + transitions stage | no |
| `log <slug> [--limit N] [--gates] [--transitions] [--json]` | read run/gate/transition history | yes | yes |
| `repair <slug>` | re-canonicalize status.yaml after partial write | yes | no |

> **Note (V0.1.1):** Only `list`, `next`, and `log` support `--json`. The
> state-changing commands print Rich-styled output to stdout/stderr. To
> parse them, look at exit codes and grep for the structured prefix
> markers below. V0.1.2 will add `--json` everywhere; until then, use exit
> codes as the primary signal.

## Exit codes (for V0.1.1 state-changing commands)

- `0` = success
- `1` = generic error (schema fail, missing packet, IO error)
- `2` = gate failure (`promote`) or an unresolvable argument

A successful `promote`'s stdout looks like:

```
promoted 2026-05-thing: discovery -> spec_ready
  ok spec/discovery.md '## Recommended Direction' is filled
  ok workflow/status.yaml::open_questions is empty
```

A failing `promote` exits 2 and stderr looks like:

```
gates failed:
  - spec/discovery.md '## Recommended Direction' is empty
  - workflow/status.yaml::open_questions is not empty (has value: ['foo'])
```

When a gate fails, **read each line as a fix-it instruction**. The
predicate evaluator names the file, the section or field, and what's
wrong. Edit the file, then re-promote.

## How to handle each user-request shape

### "Start a project on X"

1. Pick a slug from the user's description (lowercase, hyphenated,
   no date prefix — swarmlord adds `YYYY-MM-` automatically). If unsure,
   ask once.
2. Run `swarmlord new <slug> --title "<title>" --summary "<one-sentence>"`.
3. Tell the user the new packet path and that the next step is filling
   `spec/idea.md`.

### "What should I work on?"

1. Run `swarmlord next --runner-profile manual` (or just `swarmlord next`).
2. If output is "nothing dispatchable", say so. Otherwise relay the slug
   and the first next-action verbatim.

### "Move X forward"

1. Run `swarmlord render <slug>` to see the current phase's prompt and
   understand what's expected.
2. Read the spec file the prompt mentions (e.g. `spec/discovery.md`).
3. If there are gaps, fill them — but ask the user before writing
   substantive content. Don't guess at their intent.
4. Run `swarmlord promote <slug>`. If it fails, parse the gate failures
   line-by-line and fix each, then retry.
5. After success, summarize what changed in 1-2 lines.

### "What happened with X?"

1. `swarmlord log <slug> --gates --transitions --json` for full machine
   parse, or without `--json` for a human-readable view.
2. Summarize the last few interesting events, not all of them.

### "Ship X" / "Extract X"

1. Verify packet is at stage `build_ready` via `swarmlord list --json`.
2. Verify `EXTRACT.md` checkboxes are resolved (run
   `swarmlord validate <slug>` first; the gate evaluator catches it).
3. **Confirm with the user before extracting** — extraction is a
   significant action that creates a new repo and changes the source
   packet's stage. Don't extract on autopilot.
4. Run `swarmlord extract <slug> --target <path>`.
5. Never use `--force` without explicit user authorization to bypass
   gates.

### "Show me what's there"

1. `swarmlord list --json`.
2. Render as a short bulleted summary by stage; don't dump the raw JSON
   unless asked.

## Editing rules for spec/*.md files

The default gates check that markdown sections under specific headings are
**filled** and contain no forbidden tokens. The default forbidden token
list is `TBD`, `TODO`, `FIXME` — case-sensitive whole-word matches.

Don't game the gate. Writing `## Outcome\n\nyes` will technically pass the
filled-and-no-forbidden check, but the gate is catching laziness, not
stupidity. Aim for content that would actually help a future agent (or
the user themselves) understand the decision.

When the user describes work, write the relevant section to capture
intent, then ask "does this match what you meant?" before committing
substantive content. Quote the user's own phrasing where it's useful;
don't paraphrase aggressively.

## Pitfalls and conventions

**`current_phase` ≠ `stage`.** When you promote a packet across stages,
also update `status.yaml.current_phase` to match the new stage's natural
phase (`idea→idea`, `discovery→discovery`, `spec_ready→build_spec`,
`build_ready→extraction`). The orchestrator does not auto-sync them
today.

**`open_questions` blocks promotion.** Most forward transitions require
`open_questions` to be empty. When the user resolves a question, **move
it from `open_questions` to `resolved_questions`** — don't delete it.
That preserves the audit trail.

**WORKFLOW.md is authoritative.** If a packet has a
`workflow/WORKFLOW.md`, its `gates:` list is what runs — including the
empty-list case (`promote_to_spec_ready: []` means *no gates*, not "use
defaults"). Defaults only fire when no WORKFLOW.md exists.

**Path confinement.** Predicate paths like `../../etc/passwd` are
rejected by `_confine_path`. Don't try to read files outside the packet
through the gate API.

**Atomic packet writes.** Don't edit `status.yaml` and then crash — use
the orchestrator's commands (`promote`, `repair`) so writes go through
the temp-file + `os.replace` pattern. If you must edit by hand, do the
write in one operation.

**Append-only THREAD_LOG.md.** Never rewrite history. Add a dated bullet:
`- YYYY-MM-DD: short summary of what happened.`

## When NOT to act without user confirmation

- `swarmlord extract` with or without `--force` (creates a new repo,
  changes stage).
- `swarmlord promote --demote` (backward transitions; require the user's
  reason).
- Editing `spec/build-spec.md` substantively (this is the implementation
  contract; see `AGENTS.md` for change rules).
- Deleting or renaming any packet file.
- Bumping `runner_profile` to `claude-code-interactive` or
  `sandcastle-docker` (changes how runs execute).

## What to read for more

- `GUIDE.md` — the user-facing walkthrough. Re-read it if you're unsure
  what the user expects.
- `spec/build-spec.md` — the implementation contract. The full type
  system, predicate vocabulary, runner protocol, and acceptance
  criteria. Source of truth when this skill is ambiguous.
- `swarmlord <command> --help` — exact flags and defaults; trust this
  over the table above if they ever drift.
