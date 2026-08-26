# Idea

> **Historical design record.** This file captures the design as it stood
> before implementation. It is kept for provenance, not as a live roadmap —
> where it describes hosted, server, or multi-tenant phases, those were
> dropped: SwarmLord shipped as a local single-user CLI and stays that way.
> `README.md` and `AGENTS.md` describe the project as it actually is.

## Raw Idea

The user wants to set up something like the Sandcastle repo's `README.md` to work through this folder's eventual store of side projects.

The intended flow is:

1. The user outlines a basic idea they may want to do later.
2. The assistant logs and outlines it in a way that an agent could tackle.
3. Fuzzy ideas should be fleshed out through back and forth or by a discovery-oriented agent.
4. Mature ideas should become fully specified projects that can eventually move into dedicated repos.

## Interpreted Intent

This project is likely the future automation layer for the side-projects backlog. It should be able to inspect project packets, decide whether they need discovery or implementation, run the right agent workflow, preserve logs and outputs, and help promote successful work into standalone repositories.

## Why This Might Matter

The repo is intended to hold many project ideas over time. Without a durable intake and orchestration system, those ideas may remain scattered notes. A good system could let the user think loosely while still creating structured work that agents can continue later.

## Initial Assumptions

- The orchestration system should be runner-agnostic at the packet/spec level.
- Sandcastle is inspiration for isolated execution, not necessarily the required V1 dependency.
- Fuzzy projects should enter discovery before build.
- Mature projects should be extractable into dedicated repos.

## First Discovery Questions

- What is the minimum useful orchestration loop?
- Which agent runners should be supported first?
- What project metadata should decide whether an agent does discovery, spec writing, or implementation?
- Should orchestration scripts live in this repo or become their own project?
