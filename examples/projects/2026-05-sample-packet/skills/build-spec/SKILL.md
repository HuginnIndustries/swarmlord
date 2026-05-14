# Side Project Build Spec Skill

Use this skill when discovery is stable enough to create an implementation-ready handoff.

## Goal

Produce `spec/build-spec.md` so another agent can build without making product or architecture decisions.

## Instructions

1. Read `spec/idea.md`, `spec/discovery.md`, and `workflow/status.yaml`.
2. Define the intended outcome, workflows, interfaces, data, acceptance criteria, and test plan.
3. Keep the spec concrete but avoid inventing unnecessary implementation machinery.
4. Record unresolved decisions as open questions instead of hiding them.
5. Set stage to `build-ready` only when the handoff is actually actionable.

## Guardrails

- Do not make the build spec broader than the recommended MVP.
- Keep runner-specific commands out unless they are essential.
- Make acceptance criteria observable.
