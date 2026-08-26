# Examples

Runnable sample packets you can drive with the CLI without scaffolding your own. The CLI scans `./projects/<slug>/workflow/status.yaml` from the current working directory, so to use these:

```sh
cd examples
swarmlord list
swarmlord render 2026-05-sample-packet
swarmlord validate 2026-05-sample-packet
```

To follow [`GUIDE.md`](../GUIDE.md) end-to-end, make a fresh directory and run `swarmlord new` to scaffold your own packet — that's the normal flow. The packets here are read-only references for understanding what a fresh scaffold looks like.

## What's here

- [`projects/2026-05-sample-packet/`](projects/2026-05-sample-packet) — the packet `swarmlord new` produces by default. A walkthrough of the directory layout, `status.yaml` shape, and `WORKFLOW.md` predicates.
