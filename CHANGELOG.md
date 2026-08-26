# Changelog

All notable changes to SwarmLord land here. Format follows
[keepachangelog.com](https://keepachangelog.com/en/1.1.0/); this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.2.0] — 2026-08-26

### Changed

- **Project scope narrowed to a local, single-user tool.** The planned hosted
  phases (a V2 FastAPI/worker-queue daemon and a V3 multi-tenant SaaS) are
  cancelled. SwarmLord is a CLI and Python library you run on your own machine,
  and that is its final intended shape. `README.md`, `AGENTS.md`, `CLAUDE.md`,
  `GUIDE.md`, `CONTRIBUTING.md`, `SECURITY.md`, and the feature-request template
  all state the new scope.
- `README.md` rewritten for a general open-source audience: leads with what the
  tool does and how the gate model works, shows real command output, and
  documents the engineering standards. The v1/v2/v3 roadmap and the
  `swarmlord.dev` product framing are gone.
- All documentation examples converted from PowerShell to POSIX shell, and
  machine-specific paths (`~\Documents\GitHub\...`, `C:\Users\...`) replaced
  with portable ones.
- `spec/` is now explicitly labelled a historical design record. Each file
  carries a banner saying so, and the build spec's "V2 and V3 Outline" section
  is replaced by a note explaining what was dropped and why.
- CI actions bumped to current majors: `actions/checkout` v4 → v7,
  `astral-sh/setup-uv` v3 → v7, `actions/upload-artifact` v4 → v7,
  `actions/download-artifact` v4 → v8.
- `claude-code-review.yml` now skips bot-authored pull requests. Bot PRs don't
  receive repository secrets, so `CLAUDE_CODE_OAUTH_TOKEN` was empty and the
  job failed on every Dependabot bump.
- `release.yml` no longer requires PyPI. Publishing is gated behind a
  `PYPI_PUBLISH` repository variable and skipped by default, and the GitHub
  Release job now depends on `build` rather than on the publish step — so
  tagging produces a release with wheel and sdist attached whether or not a
  PyPI Trusted Publisher is configured.

### Removed

- **The `server/` FastAPI scaffold and the `swarmlord serve` command.** Every
  route returned 501 and the command exited 2; both existed only to reserve
  import paths for the cancelled hosted phase. Also removed: the `[server]`
  optional dependency group (`fastapi`, `uvicorn`), `fastapi` from the dev
  group, the `server/*` coverage omit, and `test_serve_is_v2_stub`. The test
  suite is 98 tests; coverage holds at ~85% with the omit gone.
- A 45 KB terminal-session transcript accidentally committed at the repo root.

### Added

- `Makefile` — `make check` runs all four quality gates (ruff check, ruff
  format --check, mypy --strict, pytest --cov) in one command; also `install`,
  `fmt`, `cov`, and `clean` targets.
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor
  Covenant 2.1), and `SECURITY.md` for the open-source release.
- GitHub issue templates (`bug_report.yml`, `feature_request.yml`),
  pull-request template, and an issue-template `config.yml` that routes
  questions to Discussions and security reports to private advisories.
- Dependabot config covering `pip` and `github-actions` weekly.
- `.github/workflows/release.yml` — tag-triggered build that publishes to
  PyPI via Trusted Publisher (OIDC) and creates a GitHub Release with the
  wheel + sdist attached. Verifies the tag matches the `pyproject.toml`
  version before publishing.
- `py.typed` marker (PEP 561) so downstream type-checkers pick up
  SwarmLord's annotations.
- Sample packet relocated from `projects/` to `examples/` so the live
  dispatch area starts empty for new users; existing references in
  `GUIDE.md` and the index are updated.
- Canonical operator skill at `skills/swarmlord-operator/SKILL.md` — teaches a
  coding agent (Claude Code / Codex / similar) how to drive the CLI
  conversationally.

## [0.1.1] — 2026-05-01

### Added

- `swarmlord log <slug>` reads run history, gate evaluations, and stage
  transitions back from SQLite. Flags: `--limit`, `--gates`,
  `--transitions`, `--json`.
- `extracted_to: str | None` and `extracted_on: date | None` on
  `PacketStatus` so packets that pre-date the new schema and were
  already extracted continue to validate.
- `discover_failures()` in `packets/discovery.py` and a yellow `invalid
  <slug>: <error>` block in `swarmlord list` so packets whose
  `status.yaml` exists but fails schema validation are no longer silently
  invisible.
- `--force` flag on `swarmlord extract` for emergency extraction of a
  packet that doesn't satisfy the build-ready stage and predicate gates.
- `warn_writer` callback on `ManualRunner` and a CLI-flavored runner
  registry that pipes clipboard-failure warnings to stderr; `--clipboard`
  on `render` no longer silently falls back to stdout.
- `_confine_path()` helper in `core/gates.py` and a corresponding
  "escapes the packet root" GateResult so file/yaml predicates can't be
  pointed outside the packet directory via `..` segments.

### Changed

- `service.promote` no longer silently overrides an empty
  `gates.promote_to_*` list with the built-in defaults. WORKFLOW.md is
  authoritative — declaring an empty list now means "no gates for this
  transition" and is honored.
- `service.dispatch_run` accepts an optional `history: RunHistory | None`
  and persists the `RunRecord` on **both** the success and exception
  paths. A runner crash now leaves a `status="failed"` audit row in
  SQLite with the exception text in `error`, instead of disappearing.
- The success-path `RunRecord` now copies `commits` from the runner's
  `RunResult`. Sandcastle-parsed commit SHAs survive into history.
- `service.extract_packet` requires stage `build_ready` and evaluates the
  `promote_to_extracted` gate predicates by default; pass `force=True`
  (or `--force` on the CLI) to bypass.
- New-packet slug detection uses a regex (`^\d{4}-\d{2}-`) instead of a
  hyphen-counting heuristic, fixing edge cases like `12-1234-foo`.
- Phase resolution in `service.resolve_phase` and runner-profile
  resolution in `service.resolve_runner_profile` are now extracted with
  documented precedence chains.
- Default `WorkflowDefinition` consolidated into a single
  `default_workflow_definition()` helper used by both the bundled
  template path and the synthetic-workflow path inside `dispatch_run`.
- FastAPI router construction moved fully inside `create_app()`; each
  `server/api/*.py` exposes `build_router()` instead of an
  import-time-evaluated `router` (which previously required an
  `ImportError` dance for installs without the `server` extra).
- `default_db_path()` uses `os.name == "nt"` instead of
  `sys.platform == "win32"` so `mypy --strict` keeps both POSIX and
  Windows branches reachable on either platform.
- List columns in `swarmlord list` use `overflow="fold"` on the slug so
  long slugs wrap to multiple lines instead of being truncated with `…`.
- `Stage` and `Phase` now inherit from `enum.StrEnum` instead of
  `(str, Enum)`.
- `PacketStatus` field validators coerce non-string list items in
  `next_actions` / `assumptions` / `open_questions` /
  `resolved_questions` / `owner_notes` to strings (None → `""`,
  numbers → `str(n)`, dicts → `repr`) so realistic packets remain
  loadable instead of rejecting on a single bad item.

### Fixed

- `swarmlord --version` works without a subcommand (the eager option
  callback fires before the missing-command check).
- Replaced `datetime.utcnow()` with timezone-aware `datetime.now(UTC)`
  across runners, service, storage, and memory modules.
- `resolve_packet` raises a helpful error pointing at
  `swarmlord validate <slug>` when a packet exists on disk but fails
  schema, instead of "no packet found" (which made invalid packets feel
  missing).

## [0.1.0] — 2026-05-01

### Added

- V1 implementation per `spec/build-spec.md`. Python 3.12, `uv`-managed.
- `core/`: Pydantic v2 models, `Stage`/`Phase` `StrEnum`s, transition
  table, and predicate evaluators (`FileExists`, `FileSectionFilled`,
  `YamlFieldEmpty`, `YamlFieldEquals`, `ExtractMdResolved`,
  `TestsPassing`).
- `packets/`: discovery walker, ruamel.yaml round-trip reader, atomic
  writer with `tempfile` + `os.replace`, append-only `THREAD_LOG.md`,
  `projects/INDEX.md` upsert.
- `templating/`: Jinja2 with `StrictUndefined`, `autoescape=False`,
  `keep_trailing_newline=True`, custom filters
  (`trim`/`indent_n`/`default_empty`/`summarize`), and the rule that
  user-supplied content is treated literally.
- `runners/`: Runner Protocol with `RunRequest`/`RunResult`,
  `ManualRunner` with clipboard fallback, `ClaudeCodeInteractiveRunner`,
  `SandcastleDockerRunner` that generates `.sandcastle/main.ts` +
  `prompt.md` and parses the `__SANDCASTLE_SUMMARY__` line.
- `memory/`: `graphify` subprocess wrapper.
- `storage/`: SQLite `RunHistory` at
  `~/.local/share/swarmlord/runs.db` (POSIX) or
  `%APPDATA%\swarmlord\runs.db` (Windows). Three tables: `runs`,
  `gate_evaluations`, `transitions`.
- `service.py`: orchestration glue (`list/pick/new/render/promote/
  dispatch/extract/validate`).
- `cli.py`: Typer entry point with the 11 commands from the spec.
- `server/`: FastAPI scaffold returning 501 from every endpoint, ready
  for V2 to fill in.
- Bundled packet template at `src/swarmlord/_templates/packet/` (used as
  fallback when `<repo>/templates/packet/` is absent).
- `.github/workflows/ci.yml`: lint, format check, `mypy --strict`,
  `pytest --cov` with an 80% coverage gate.

[Unreleased]: https://github.com/HuginnIndustries/swarmlord/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/HuginnIndustries/swarmlord/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/HuginnIndustries/swarmlord/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/HuginnIndustries/swarmlord/releases/tag/v0.1.0
