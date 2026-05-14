# Security Policy

## Supported versions

SwarmLord is pre-1.0 (currently `0.1.x`). Security fixes ship on the latest minor release only. Older releases are not patched.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Please use [GitHub private vulnerability reporting](https://github.com/HuginnIndustries/swarmlord/security/advisories/new) instead. Include:

- A description of the vulnerability and its impact.
- Steps to reproduce, ideally with a minimal proof-of-concept.
- Affected version(s) and platform.
- Any suggested mitigation, if you have one.

You should receive an acknowledgement within 5 business days. We aim to publish a fix and an advisory within 30 days for confirmed issues; complex cases may take longer and we'll keep you updated.

## Scope

In scope:

- The `swarmlord` Python package, CLI, and bundled templates.
- The CI workflows and release pipeline in `.github/workflows/`.

Out of scope:

- Third-party runners (`claude`, Sandcastle, `npx`, `tsx`) invoked as subprocesses. Report those upstream.
- Vulnerabilities that require a malicious local user to already have shell access on the host running SwarmLord — the V1 model trusts the operator's machine.
- The `server/` FastAPI scaffold, which returns 501 from every endpoint by design and has no behavior to exploit.
