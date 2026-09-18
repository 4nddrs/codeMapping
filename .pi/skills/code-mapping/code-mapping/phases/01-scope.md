# Phase 1 — Scope

**Gate out:** filled `BRIEF.md` approved by the user (or explicitly marked draft with open questions listed).

## Purpose

Freeze **what** is being mapped so later phases do not sprawl.

## Steps

1. Identify the **canonical command** (exact argv the team cares about).
2. Identify **environment** needs (env vars names only — never paste secrets into the brief; point to `.env.example`).
3. Define **SUCCESS** criteria (exit code, reward, assertion, golden log line, etc.).
4. Define **FAILURE** scenario of interest (optional but recommended for abort edges).
5. List **in scope** modules / packages and **out of scope** areas.
6. Note known complications (caches, remote tools, GPU, flaky deps).
7. Choose the **artifact root** (default `docs/code_mapping/`).
8. Write the brief using [../templates/brief.template.md](../templates/brief.template.md).

## Questions to ask the user if unclear

- Which single command / scenario is the unit of study?
- Where do successful run outputs already live?
- Is there a preferred FAILURE case?
- Which subsystems must be excluded (codegen, benchmarks, other robots, UI)?

## Anti-patterns

- Mapping “the whole product.”
- Multiple unrelated commands in one brief.
- SUCCESS criteria that cannot be checked from artifacts.

## Next

Phase 2 — Capture.
