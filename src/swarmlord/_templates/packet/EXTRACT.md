# Extraction Checklist

Use this checklist when the project is ready to become a standalone GitHub repo.

## Before Extraction

- [ ] `spec/build-spec.md` is complete enough for implementation.
- [ ] `README.md` clearly states the project purpose and current status.
- [ ] Project-local `skills/` are present and relevant.
- [ ] `THREAD_LOG.md` contains useful handoff context.
- [ ] Open questions in `workflow/status.yaml` are either resolved or explicitly deferred.

## New Repo Setup

- [ ] Create a dedicated repo under the GitHub folder.
- [ ] Copy `README.md`, `GUIDE.md`, `spec/`, `workflow/`, `skills/`, and `THREAD_LOG.md`.
- [ ] Add implementation scaffolding appropriate to the build spec.
- [ ] Initialize Git in the extracted repo.
- [ ] Update this packet's `workflow/status.yaml` to `extracted`.
- [ ] Update the root `projects/INDEX.md` with the destination repo path or URL.

## Leave Behind

Keep this packet as the historical source of the idea and extraction record. Do not delete it unless the user explicitly asks.
