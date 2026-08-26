# Contributing to SwarmLord

Thanks for considering a contribution. SwarmLord is a small, opinionated tool — the easiest way to land a change is to keep PRs focused and aligned with the existing architecture.

## Before opening a PR

- For anything beyond a typo or one-line fix, open an issue first to confirm scope. This avoids wasted work on changes we'd reject for design reasons.
- Read [`AGENTS.md`](AGENTS.md) and [`spec/build-spec.md`](spec/build-spec.md). Several decisions are locked in (Pydantic v2, Jinja2 `StrictUndefined`, Typer, SQLite, the runner set, the stage/phase enums) — please don't relitigate them in a PR.

## Dev setup

You need [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```sh
git clone https://github.com/HuginnIndustries/swarmlord.git
cd swarmlord
uv sync --dev
uv run swarmlord --help
```

## Quality gates

All four must pass locally and in CI before a PR can merge:

```sh
make check                          # all four at once
```

Or individually:

```sh
uv run ruff check
uv run ruff format --check          # drop --check to auto-format
uv run mypy --strict src/swarmlord
uv run pytest                       # 98 tests, ~85% coverage; gate is 80%
```

Useful subsets:

```sh
uv run pytest tests/test_service.py             # one file
uv run pytest tests/test_service.py::test_x     # one test
uv run pytest -k promote                        # by keyword
```

`pytest` runs with `filterwarnings = ["error", ...]` — any unhandled warning fails the test.

## Conventions

- **Atomic packet writes only.** Never write directly to `status.yaml` or append to `THREAD_LOG.md` mid-stream — go through the helpers in `packets/writer.py`.
- **`StrictUndefined` everywhere.** User-supplied content is inserted as already-rendered strings; the template engine never re-evaluates it.
- **Pydantic models forbid extras.** If a field is missing from a real-world packet, prefer adding it to the schema over loosening config. `extracted_to`/`extracted_on` are precedent.
- **Path confinement.** All file-targeted predicates are confined to the packet directory. `..` and absolute paths are rejected.
- **Dates.** Convert relative dates to absolute `YYYY-MM-DD` before persisting anything user-visible (slugs, `status.yaml`, `THREAD_LOG.md` entries).

## What to avoid

- Speculative abstractions or "future-proofing" beyond the task at hand. Three similar lines is better than a premature abstraction.
- Comments that restate what the code does. Only comment the *why* when it's non-obvious.
- Backwards-compatibility shims, "removed-feature" placeholders, or unused re-exports.
- Adding unit tests against `runners/claude_code.py` — it shells out to a real binary CI can't run, and is excluded from coverage.
- Anything that turns SwarmLord into a service: an HTTP server, auth, tenancy, or hosted state. It is a local single-user tool by design.

## PR checklist

- [ ] One focused change per PR.
- [ ] All four quality gates pass locally.
- [ ] If user-visible: a [`CHANGELOG.md`](CHANGELOG.md) entry under `[Unreleased]`.
- [ ] If a milestone: README "Status" section updated.

## Reporting bugs

Use the bug report issue template. The most useful reports include:

- The exact `swarmlord` command and its full output.
- The contents of the packet's `workflow/status.yaml`.
- `swarmlord --version`, your OS, and your Python version.

## Reporting security issues

Don't open a public issue. See [`SECURITY.md`](SECURITY.md) for the disclosure process.
