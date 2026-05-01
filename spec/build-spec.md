# Build Spec

This file is implementation-ready. Another agent should be able to build v1 from it without making structural product decisions. Architectural choices, schemas, interfaces, and acceptance criteria are settled here. Trade-off discussion that led to these choices lives in `spec/inspiration-review.md` and `spec/discovery.md`.

Project name: **SwarmLord**. CLI binary: `swarmlord` (with `swarm` available as an alias if desired). Python package: `swarmlord`. Repo name at extraction: `swarmlord`. Domain: `swarmlord.dev` (owned, planned customer-facing surface for V3 SaaS). The originating folder slug `2026-05-sandcastle-like-agent-orchestration` remains as a historical trace of where the idea started; the implementation does not inherit it.

## Outcome

A Python service that turns side-project packets into agent-executable work. The packet model is the same one this repo already uses: a folder under `projects/<slug>/` containing durable Markdown specs, a `workflow/status.yaml` of state, and an optional `workflow/WORKFLOW.md` policy file. The service reads packets, knows which one is dispatchable, renders a prompt for the packet's current phase, dispatches the prompt to a runner (manual, interactive Claude Code, or Sandcastle Docker), and writes results back into the packet atomically.

V1 ships as a local CLI plus a Python library. V2 adds a FastAPI HTTP surface and a worker queue so the same engine can run as a server-hosted daemon. V3 layers multi-tenant SaaS concerns (tenant isolation, auth, billing, admin UI) on top of V2 without changing the core. The architecture explicitly plans for V2 and V3; v1 must not foreclose them.

The service replaces the in-repo `pipeline.yaml` with code. Phases, stages, and state transitions become typed first-class concepts in the orchestrator; YAML and Markdown remain the per-packet content layer.

## User Workflows

### Workflow A — Capture a fuzzy idea

User runs `swarmlord new <slug> --title "..."`. The CLI scaffolds `projects/YYYY-MM-<slug>/` from the templates folder, fills `workflow/status.yaml` with `stage: idea` and a sensible `next_actions[0]`, and adds the packet to `projects/INDEX.md`. No `WORKFLOW.md` is created at this stage; the packet is plain Markdown until it reaches `spec_ready`.

### Workflow B — Move ideas through discovery

User runs `swarmlord next`. The CLI walks every `projects/*/workflow/status.yaml`, filters for dispatchable packets, sorts by stage and oldest-pending, and prints the top candidate's `next_actions[0]` along with the runner profile that should pick it up. `swarmlord render <slug>` produces the prompt for that packet's current phase as text on stdout (or copies to clipboard on `--clipboard`). The user can paste it into Claude Code or Codex by hand. This is the v1 happy path — manual dispatch with rendered prompts.

### Workflow C — Run a build agent autonomously

Once a packet reaches `build_ready` (gates pass), the user runs `swarmlord run <slug> --runner sandcastle-docker`. The orchestrator invokes Sandcastle as a subprocess against the extracted target directory (or against a worktree of this repo for in-repo work), forwards Sandcastle's structured output, and writes a run record back into the packet's `workflow/runs/<timestamp>.yaml`. On success, the packet transitions to `extracted` (or stays `build_ready` if `max_turns` was hit and continuation is wanted).

### Workflow D — Promote a stage

User runs `swarmlord promote <slug>`. The orchestrator evaluates the gate predicates declared for the next stage (in `workflow/WORKFLOW.md` front matter, or built-in defaults). It either updates `status.yaml.stage`, writes `THREAD_LOG.md`, and updates `projects/INDEX.md`, or prints the failing predicates with concrete reasons.

### Workflow E — Build packet memory

User runs `swarmlord graphify <slug>` to build a Graphify graph inside the packet (`projects/<slug>/graphify-out/`). User runs `swarmlord graphify --repo` to build a repo-wide graph at `graphify-out/`. The orchestrator wraps the `graphify` CLI as a subprocess, captures the GRAPH_REPORT.md path, and registers it in the packet's status so subsequent prompt renders can reference it.

### Workflow F — Extract to standalone repo

User runs `swarmlord extract <slug> --target ~/Documents/GitHub/<repo>`. The orchestrator validates `EXTRACT.md`, creates the target directory, copies the packet's `README.md`, `GUIDE.md`, `spec/`, `workflow/`, `skills/`, and `THREAD_LOG.md`, initializes git, scaffolds language-appropriate project files based on `WORKFLOW.md.runner_profile`, sets `status.yaml.stage = extracted`, and updates `projects/INDEX.md` with the destination path. Per the existing EXTRACT.md, the original packet stays in this repo as historical record.

### Workflow G — Run as a server (V2, scaffolded in V1)

The same core library is consumable from a FastAPI app. `swarmlord serve` boots a local instance for development; production deploys via container. API surface mirrors the CLI: list packets, render prompts, dispatch runs, evaluate gates, promote stages, watch packet directory for changes. Long-running dispatches are handled by a worker process consuming a queue. V1 scaffolds the server module but does not implement endpoints; V2 fills it in.

## Implementation Direction

### Language and tooling

Python 3.12. Project managed with `uv` (`uv venv`, `uv pip install`, `uv run`). `pyproject.toml` is the source of truth for dependencies and scripts. Linting via `ruff`, formatting via `ruff format`, type checking via `mypy --strict` (or `pyright` if it integrates better). Test runner is `pytest` with `pytest-asyncio` for async paths and `pytest-cov` for coverage.

### Core libraries

`pydantic` v2 for schema validation (packet `status.yaml`, `WORKFLOW.md` front matter, run records, gate predicates, runner options). `jinja2` with `StrictUndefined` for prompt templating. `typer` for the CLI surface (Click under the hood; matches FastAPI's idiomatic Python style). `ruamel.yaml` for round-trip YAML so writes to `status.yaml` preserve comments and ordering. `python-frontmatter` for parsing `WORKFLOW.md`. `httpx` for outbound HTTP if the runner needs it. `rich` for CLI output formatting.

### Deferred libraries (V2)

`fastapi` + `uvicorn` for the HTTP surface. `arq` (preferred over Celery for an async-native worker queue with a smaller dependency footprint) for background jobs. `asyncpg` + `sqlalchemy` 2.x async for Postgres. `alembic` for migrations.

### Architecture layers

The package is structured so each layer has one clear responsibility and no upward dependency. The CLI depends on the library, never the reverse.

```
src/swarmlord/
    __init__.py
    core/
        __init__.py
        models.py          # Pydantic: PacketStatus, WorkflowDefinition, RunRecord, etc.
        stages.py          # Stage enum + transition table
        phases.py          # Phase enum
        gates.py           # Predicate evaluators
        errors.py          # Typed exceptions
    packets/
        __init__.py
        discovery.py       # Walk repo and find packets
        reader.py          # Load a packet's status.yaml + WORKFLOW.md
        writer.py          # Atomic writes back to packet (write-temp + os.replace)
        thread_log.py      # Append to THREAD_LOG.md
        index.py           # Read/write projects/INDEX.md
    templating/
        __init__.py
        engine.py          # Jinja2 Environment with StrictUndefined + sandboxing
        filters.py         # Custom filters (trim, indent, default_empty)
    runners/
        __init__.py
        base.py            # Runner protocol + RunRequest/RunResult dataclasses
        manual.py          # Print/clipboard runner (no agent invocation)
        claude_code.py     # Interactive Claude Code via subprocess
        sandcastle.py      # Sandcastle subprocess runner
        registry.py        # Profile string -> runner instance
    memory/
        __init__.py
        graphify.py        # Subprocess wrapper around the graphify CLI
    storage/
        __init__.py
        run_history.py     # SQLite-backed run record store (V1)
                           # Postgres path comes in V2 via SQLAlchemy
    cli.py                 # Typer entry point; thin layer over the library
    server/                # V2 scaffold; v1 leaves stubs only
        __init__.py
        app.py             # FastAPI app factory
        api/
            __init__.py
            packets.py
            runs.py
            gates.py
        worker.py          # arq worker entry
tests/
    fixtures/
        packets/           # Sample packets in every stage
        workflows/         # Sample WORKFLOW.md files
    test_models.py
    test_stages.py
    test_gates.py
    test_packets_reader.py
    test_packets_writer.py
    test_templating.py
    test_runners_manual.py
    test_runners_sandcastle.py  # subprocess mocked
    test_cli.py
    test_integration_full_cycle.py
templates/
    packet/                # Copied into projects/YYYY-MM-<slug>/ on `swarmlord new`
        README.md
        GUIDE.md
        EXTRACT.md
        THREAD_LOG.md
        workflow/
            status.yaml
            WORKFLOW.md
        spec/
            idea.md
            discovery.md
            build-spec.md
```

### Sandcastle as a subprocess

V1 calls Sandcastle through its CLI, not its Node API. The orchestrator generates the `.sandcastle/main.ts` and `.sandcastle/prompt.md` files in the target directory, then runs `npx sandcastle ...` (or `tsx .sandcastle/main.ts`) and parses the stdout/stderr stream. `claudeCode` model and effort, branch strategy, sandbox provider, hooks, and completion signal are configurable per packet via `WORKFLOW.md`. Sandcastle's session JSONL output is captured by Sandcastle itself; the orchestrator records only the path and exit code.

If at some point the cost of subprocess parsing exceeds the cost of duplicating Sandcastle's logic, revisit. For v1, the subprocess boundary is correct.

### Templating contract

Templates live in `WORKFLOW.md`'s body. The engine is `jinja2.Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)`. Variables are passed through a typed context object built from the packet's `PacketStatus` plus per-run extras (`attempt`, `prior_run_summary`, `repo_root`, `packet_root`, `graph_report_path`). `promptArgs`-equivalent values from caller-supplied data are inserted as already-rendered strings — the template engine never re-evaluates user-supplied content. Custom filters: `trim`, `indent(n)`, `default_empty`, `summarize(n_words)`. Tests assert that an unknown variable raises and that user-supplied content containing `{{` or `{%` is treated as literal.

### State machine

Stages and their legal transitions are defined as code, not YAML.

```
idea       -> discovery, archived
discovery  -> spec_ready, idea, archived
spec_ready -> build_ready, discovery, archived
build_ready-> extracted, spec_ready, archived
extracted  -> archived
archived   -> (terminal)
```

Promotion forward requires gate predicates to pass. Demotion back is always allowed (with a `--reason` argument that gets written to `THREAD_LOG.md`).

### Atomicity

All packet writes use the temp-file-and-rename pattern (`tempfile.NamedTemporaryFile` in the same directory, then `os.replace`). When multiple files must change together (e.g. `status.yaml`, `THREAD_LOG.md`, and `projects/INDEX.md` during a stage promotion), the orchestrator builds the new contents in memory, validates schemas, and only then performs the renames sequentially. If any rename fails, already-renamed files are not rolled back automatically — the run record captures the partial state, and `swarmlord repair <slug>` reconciles by re-validating from disk. V2 adds a SQLite write-ahead log for true crash safety.

### Storage

V1: SQLite at `~/.local/share/swarmlord/runs.db` (or `%APPDATA%\swarmlord\runs.db` on Windows). Schema: `runs(id, packet_slug, runner_profile, started_at, ended_at, exit_code, prompt_hash, log_path, status)`, `gate_evaluations(run_id, predicate, passed, message)`, `transitions(packet_slug, from_stage, to_stage, at, reason)`. Pydantic models map to rows.

V2: Same schema in Postgres via SQLAlchemy 2.x async. SQLite remains supported as a local-dev mode.

## Interfaces and Data

### Stage enum

```python
class Stage(str, Enum):
    IDEA = "idea"
    DISCOVERY = "discovery"
    SPEC_READY = "spec_ready"
    BUILD_READY = "build_ready"
    EXTRACTED = "extracted"
    ARCHIVED = "archived"
```

### Phase enum

```python
class Phase(str, Enum):
    IDEA = "idea"
    DISCOVERY = "discovery"
    BUILD_SPEC = "build_spec"
    EXTRACTION = "extraction"
    MEMORY = "memory"  # transient; runs graphify and returns to prior phase
```

### PacketStatus model

Maps directly to `workflow/status.yaml`. Fields:

- `project_name: str`
- `slug: str` (must match folder name)
- `stage: Stage`
- `current_phase: Phase`
- `created: date`
- `updated: date`
- `summary: str`
- `next_actions: list[str]`
- `assumptions: list[str]`
- `open_questions: list[str]`
- `resolved_questions: list[str]`
- `phase_status: dict[Phase, Literal["pending", "in_progress", "complete", "skipped"]]`
- `owner_notes: list[str]`
- `runner_profile: str | None` (overrides WORKFLOW.md if set)
- `memory: MemoryStatus | None` (when graphify has been run)

### WorkflowDefinition model

Parsed from `workflow/WORKFLOW.md`. Front matter is the YAML config; body is the prompt template.

```python
class WorkflowDefinition(BaseModel):
    runner_profile: str
    phase: Phase
    hooks: WorkflowHooks
    agent: AgentConfig
    gates: GateConfig
    prompt_template: str  # the markdown body, populated from the file body
```

`WorkflowHooks` mirrors Symphony's shape: `after_create`, `before_run`, `after_run`, `before_remove`, all `str | None`, plus `timeout_ms: int = 60000`.

`AgentConfig`: `max_turns: int = 20`, `stall_timeout_ms: int = 300_000`, `max_retry_backoff_ms: int = 300_000`, `completion_signal: str | list[str] = "<promise>COMPLETE</promise>"`, `idle_timeout_seconds: int = 600`.

`GateConfig`:

```python
class GateConfig(BaseModel):
    promote_to_spec_ready: list[Predicate] = []
    promote_to_build_ready: list[Predicate] = []
    promote_to_extracted: list[Predicate] = []
```

### Predicate vocabulary

Gates are declarative and machine-checkable. Every predicate has a single typed shape and a deterministic evaluator. No natural-language predicates.

```python
class FileExists(BaseModel):
    kind: Literal["file_exists"]
    path: str  # relative to packet root

class FileSectionFilled(BaseModel):
    kind: Literal["file_section_filled"]
    path: str
    section: str           # e.g. "## Outcome"
    forbidden_tokens: list[str] = ["TBD", "TODO", "FIXME"]

class YamlFieldEmpty(BaseModel):
    kind: Literal["yaml_field_empty"]
    path: str               # e.g. "workflow/status.yaml"
    field: str              # dotted path: "open_questions" or "phase_status.discovery"

class YamlFieldEquals(BaseModel):
    kind: Literal["yaml_field_equals"]
    path: str
    field: str
    value: str | int | bool

class ExtractMdResolved(BaseModel):
    kind: Literal["extract_md_resolved"]
    # checks all checkboxes resolved or explicitly marked deferred

class TestsPassing(BaseModel):
    kind: Literal["tests_passing"]
    command: str            # shell command run in packet root, exit 0 = pass

Predicate = Annotated[
    FileExists | FileSectionFilled | YamlFieldEmpty | YamlFieldEquals
    | ExtractMdResolved | TestsPassing,
    Field(discriminator="kind"),
]
```

Default gates (used when a packet has no `WORKFLOW.md` or its gates are empty):

- `discovery -> spec_ready`: `FileSectionFilled(spec/discovery.md, "## Recommended Direction")`, `YamlFieldEmpty(workflow/status.yaml, "open_questions")`.
- `spec_ready -> build_ready`: `FileSectionFilled(spec/build-spec.md, "## Outcome")`, `FileSectionFilled(spec/build-spec.md, "## Acceptance Criteria")`, `FileSectionFilled(spec/build-spec.md, "## Test Plan")`, `YamlFieldEmpty(workflow/status.yaml, "open_questions")`, `ExtractMdResolved`.
- `build_ready -> extracted`: `FileExists(EXTRACT.md)`, `ExtractMdResolved`.

### Runner protocol

```python
class RunRequest(BaseModel):
    packet_slug: str
    packet_root: Path
    rendered_prompt: str
    workflow: WorkflowDefinition
    runner_options: dict[str, Any] = {}

class RunResult(BaseModel):
    runner: str
    started_at: datetime
    ended_at: datetime
    exit_code: int
    completion_signal_seen: str | None
    log_path: Path | None
    transcript_path: Path | None  # session JSONL if Sandcastle
    commits: list[str] = []        # SHAs if applicable
    error: str | None = None

class Runner(Protocol):
    name: str
    def can_handle(self, profile: str) -> bool: ...
    async def run(self, request: RunRequest) -> RunResult: ...
```

V1 runners:

- `manual`: Renders the prompt, copies to clipboard (via `pyperclip`) or writes to a temp file, prints instructions, returns immediately with `exit_code=0`. No agent invocation.
- `claude-code-interactive`: Spawns `claude` CLI in the packet root with the rendered prompt as initial input. User interacts directly. Returns when the process exits.
- `sandcastle-docker`: Generates `.sandcastle/main.ts` and `.sandcastle/prompt.md` in the target directory, runs `npx tsx .sandcastle/main.ts` (or `npx sandcastle init` first if not initialized), streams output, parses Sandcastle's JSON summary line at exit, returns.

### CLI surface

Implemented with Typer. Each command is a thin wrapper over the library.

```
swarmlord list [--stage X] [--phase Y]
    Show all packets, filtered, with stages.

swarmlord next [--stage X] [--runner-profile P]
    Print the top dispatchable packet and its next action.

swarmlord new <slug> [--title TITLE] [--summary TEXT]
    Scaffold a new packet from templates/packet/.

swarmlord render <slug> [--phase Y] [--attempt N] [--clipboard]
    Render the prompt for the packet's current (or specified) phase.

swarmlord run <slug> [--runner PROFILE] [--dry-run]
    Render and dispatch via the specified runner. Defaults to packet's runner_profile.

swarmlord promote <slug> [--to STAGE] [--reason REASON] [--demote]
    Run gate predicates and transition stage. --demote skips gates.

swarmlord validate <slug | --all>
    Schema-validate one packet or every packet in the repo.

swarmlord graphify <slug | --repo> [--update] [--watch]
    Wrap the graphify CLI to build/refresh memory.

swarmlord extract <slug> --target PATH
    Execute the EXTRACT.md checklist into a new repo path.

swarmlord repair <slug>
    Re-derive consistent state from disk after a partial-write failure.

swarmlord serve [--port N]
    V2: start the FastAPI server. V1 prints "not implemented".
```

### `WORKFLOW.md` location and shape

Lives at `projects/<slug>/workflow/WORKFLOW.md`, beside `status.yaml`. Front matter is the config; body is the Jinja2 prompt template.

Example:

```markdown
---
runner_profile: claude-code-interactive
phase: discovery
hooks:
  after_create: |
    echo "packet ready"
  before_run: null
  after_run: null
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
---

You are continuing discovery on packet `{{ packet.slug }}`.

Current stage: {{ packet.stage }}.
Current phase: {{ packet.current_phase }}.

{% if attempt %}
This is retry attempt {{ attempt }}. Resume from the existing spec/discovery.md
without re-doing finished sections.
{% endif %}

Open questions:
{% for q in packet.open_questions %}
- {{ q }}
{% endfor %}

{% if graph_report_path %}
A knowledge graph for this packet exists at `{{ graph_report_path }}`.
Read GRAPH_REPORT.md before grepping raw files.
{% endif %}

Update spec/discovery.md and workflow/status.yaml when done.
Append a THREAD_LOG.md entry. Emit `<promise>COMPLETE</promise>` to finish.
```

### Run record schema

Stored in SQLite (V1) and `projects/<slug>/workflow/runs/<timestamp>.yaml` for human-readable inspection. Per run: `id`, `packet_slug`, `runner_profile`, `phase`, `attempt`, `prompt_hash`, `started_at`, `ended_at`, `exit_code`, `completion_signal_seen`, `log_path`, `transcript_path`, `commits`, `transitions_triggered`.

## Acceptance Criteria

The implementation is correct when:

1. `swarmlord list` enumerates all packets currently under `projects/` with correct stages and phases derived from each `workflow/status.yaml`.
2. `swarmlord validate --all` passes against this repo's existing packets after they are migrated to the new schema (the migration adds `resolved_questions` and `runner_profile`, drops nothing).
3. `swarmlord new sample-packet` produces a packet that `swarmlord validate` passes immediately.
4. `swarmlord render` for a packet at `discovery` stage produces a deterministic prompt; given identical inputs, the rendered output is byte-identical across runs.
5. Jinja2 strict mode raises on a typo in any variable name; tests cover this with a deliberately-broken template fixture.
6. User-supplied content containing `{{` and `{% %}` characters passes through `promptArgs`-style insertion without re-evaluation; tests assert literal preservation.
7. `swarmlord promote <slug>` evaluates every declared predicate, prints which ones pass and fail, and refuses to transition unless all pass. The output identifies the failing file and section concretely (e.g. "spec/build-spec.md '## Outcome' contains 'TBD' which is forbidden").
8. `swarmlord promote <slug> --demote --reason "..."` allows backward transitions and writes the reason to `THREAD_LOG.md`.
9. `swarmlord run --runner manual` writes the rendered prompt to clipboard (or stdout with `--no-clipboard`), records a run with `exit_code=0`, and updates `phase_status` accordingly.
10. `swarmlord run --runner sandcastle-docker` invokes Sandcastle as a subprocess (mocked in tests), parses its output, records commits and transcript path, and returns a `RunResult`. Real Sandcastle integration is exercised in a manual smoke test against a throwaway packet.
11. Packet writes are atomic. A test simulates an interrupted write by patching `os.replace` to fail mid-batch and asserts the on-disk packet remains parseable.
12. `swarmlord graphify <slug>` runs the `graphify` CLI in the packet's root, captures the output paths, and updates `status.yaml.memory` with `{ graph_path, report_path, generated_at }`. Subsequent `swarmlord render` calls include `graph_report_path` in the template context.
13. `swarmlord extract <slug> --target <path>` produces a target directory containing `README.md`, `GUIDE.md`, `spec/`, `workflow/`, `skills/`, and `THREAD_LOG.md`, initializes git, and updates the source packet's `status.yaml.stage` to `extracted` plus `projects/INDEX.md`.
14. The CLI prints clear, actionable error messages on schema validation failure (Pydantic v2 errors are reformatted for humans, not dumped raw).
15. `mypy --strict` passes on the entire package. `ruff check` and `ruff format --check` pass.
16. Test coverage is at least 80% on `core/`, `packets/`, `templating/`, `runners/manual.py`, and the gate evaluators. `runners/sandcastle.py` is covered against a subprocess mock.
17. The package installs cleanly via `uv pip install -e .` and `swarmlord --help` prints the full command list.
18. The `server/` module is present as a scaffold (FastAPI app factory that returns 501 on every endpoint) so V2 work can begin without restructuring the package.

## Test Plan

### Unit tests

- **Schema** (`test_models.py`): valid and invalid `status.yaml` fixtures. Required field omission. Wrong-type values. Unknown stage/phase strings. Round-trip preservation of comments via `ruamel.yaml`.
- **State machine** (`test_stages.py`): every legal transition succeeds; every illegal transition raises `IllegalTransition`; demotion always succeeds with a reason.
- **Gates** (`test_gates.py`): each predicate type has positive and negative fixtures. Section-filled checks against several forbidden-token configurations. YAML-field-empty walks dotted paths correctly.
- **Workflow parsing** (`test_workflow_parsing.py`): valid `WORKFLOW.md` parses into `WorkflowDefinition`; missing front matter falls back to defaults; non-map front matter errors; body becomes `prompt_template`.
- **Templating** (`test_templating.py`): known variable renders; unknown variable raises; user-supplied `{{` literal preserved; conditional blocks fire correctly; custom filters work.
- **Packet I/O** (`test_packets_reader.py`, `test_packets_writer.py`): read returns expected `PacketStatus`; write round-trips through disk; atomic rename simulated failure leaves disk parseable.
- **Manual runner** (`test_runners_manual.py`): no-clipboard mode writes to stdout; clipboard mode is mocked; `RunResult` structure correct.
- **Sandcastle runner** (`test_runners_sandcastle.py`): subprocess mocked via `pytest-mock`; happy path, non-zero exit path, malformed Sandcastle output path.
- **CLI** (`test_cli.py`): each command tested via Typer's `CliRunner`. Help text, exit codes, JSON output mode (`--json`).

### Integration tests

- **Full discovery cycle** (`test_integration_full_cycle.py`): a fixture packet starts at `idea`. The test scripts: `swarmlord new` → `swarmlord render` (idea phase) → simulate manual completion of `spec/idea.md` → `swarmlord promote` → `swarmlord render` (discovery) → simulate completion → `swarmlord promote` → `spec_ready`. Asserts `THREAD_LOG.md` accumulates entries, `projects/INDEX.md` updates, gate predicates fire.
- **Multi-packet discovery** (`test_integration_multi_packet.py`): three fixture packets at different stages. `swarmlord list` and `swarmlord next` return the right candidates and ordering.

### Manual smoke tests (documented, not automated in v1)

- Run the orchestrator against this very packet (`projects/2026-05-sandcastle-like-agent-orchestration/`). `swarmlord list`, `swarmlord next`, `swarmlord render` should work without modification.
- Run a real Sandcastle invocation against a throwaway packet that asks Claude Code to add a single comment to a file.
- Run `swarmlord graphify --repo` against the side-projects repo and inspect the resulting `graphify-out/`.

### CI

GitHub Actions: matrix on Python 3.12 (later: add 3.13). Steps: `uv sync`, `ruff check`, `ruff format --check`, `mypy --strict`, `pytest --cov`. Coverage gate: 80% on the layers listed above.

## Extraction Notes

This packet stays in `side-projects/` as the historical record of the design.

The implementation extracts to a new repo named `swarmlord` at `~/Documents/GitHub/swarmlord/`.

Extraction steps:

1. Create `~/Documents/GitHub/<name>/`.
2. Initialize uv project: `uv init --package`.
3. Copy `templates/packet/` from this packet into the new repo's `templates/packet/`.
4. Implement the package per the directory layout above.
5. Add CI workflow (lint, type-check, test).
6. Add a `README.md` that explains: what the orchestrator does, how to install, how to run `swarmlord list / next / render / run / promote / graphify`, the v1 → v2 → v3 roadmap.
7. Update `projects/INDEX.md` in this repo to note the extracted destination.
8. Update this packet's `status.yaml.stage` to `extracted`.

The orchestrator can subsequently be installed back into this side-projects repo via `uv pip install <path-or-url>` so it operates on the very repo that designed it. That's the dogfood loop.

## V2 and V3 Outline (informational; not implementer scope)

V2 — server: FastAPI app exposing the same operations as the CLI; arq worker queue for background dispatch; webhook receivers for git events and tracker events; `swarmlord serve` boots the local dev instance; Postgres replaces SQLite. Gate predicate `tests_passing` becomes useful in V2 because the server can run gates against ephemeral worktrees.

V3 — SaaS: tenant isolation at the storage and worker layers; SSO auth (OIDC); per-tenant secrets; an admin UI (separate front-end repo, likely SvelteKit or Next.js); usage metering and budgets per tenant (lift Paperclip's heartbeat-budget shape); a marketplace surface for shared packet templates and runner profiles. Multi-tenancy is the only real architectural shift V3 introduces; everything else is scaling and polish. Customer-facing surface is `swarmlord.dev` (owned). Suggested subdomain plan: `swarmlord.dev` for the marketing site, `app.swarmlord.dev` for the tenant dashboard, `api.swarmlord.dev` for the V2/V3 HTTP API, `docs.swarmlord.dev` for documentation, `<tenant>.swarmlord.dev` (or path-based `app.swarmlord.dev/<tenant>/`) for tenant-scoped routes — final shape decided when V3 design begins.

## Open Items Resolved In This Spec

- `pipeline.yaml` is replaced by code. The packet's `pipeline.yaml` becomes informational only and will be removed during the v1 implementation's first migration pass.
- `WORKFLOW.md` lives at `workflow/WORKFLOW.md`, alongside `status.yaml`.
- Prompt template language is Jinja2 with `StrictUndefined`.
- The picker is a Python CLI built with Typer.
- Graphify runs on demand via `swarmlord graphify`. Idea/discovery phases do not auto-run it; auto-run is a V2 enhancement gated by a per-packet flag.
- Skills are copied on packet creation from `templates/packet/skills/` (no symlinks, no shared registry yet). A skill registry is a V2 enhancement.
- Project name is **SwarmLord** (locked — domain `swarmlord.dev` is owned). Python package and CLI binary are both `swarmlord`. Folder slug for this packet (`2026-05-sandcastle-like-agent-orchestration`) is preserved as historical trace; the extracted repo is named `swarmlord`.
