# Phase 6 — Documentation

**Gate in:** brief, important list, live I/O, gaps are frozen (or waivers recorded).<br>
**Gate out:** durable mapping document that supports Next/Back reading; optional figures.

## Purpose

Materialize the forensic story for humans. This phase **consumes** prior artifacts; it does not invent new “facts.”

## Primary deliverable

A Markdown mapping doc (`MAPPING.md`) and/or a PDF built from the same content.

Use [../templates/mapping-doc.outline.md](../templates/mapping-doc.outline.md).

Minimum sections:

1. What is being mapped (command + SUCCESS criteria)
2. How to read this document
3. Architecture / layers (high level)
4. Bootstrap / entry sequence
5. Orchestration graph (if any)
6. Live trial summary (metrics + pointer to run)
7. Function catalog (cards) in execution order
8. Failure / abort path
9. Gaps and caveats
10. Index of symbols → section

## Function cards

For each critical-path symbol, use [../templates/function-card.template.md](../templates/function-card.template.md):

- identity (path, symbol, lines)
- why
- full function or faithful extract
- inputs / outputs with **recorded** values
- next / on_failure
- gap refs

## Figures (optional but valuable)

See [../reference/diagram-types.md](../reference/diagram-types.md). Prefer diagrams that mirror the trial:

- layered architecture
- bootstrap sequence
- orchestration / workflow
- function flow (SUCCESS)
- dataflow for one hot path
- scheduler / concurrency model if relevant
- failure path
- one figure annotated with **live numbers**

Store under `docs/code_mapping/figures/`.

## Writing rules

- Past tense for what the trial did; present tense for what the code does in general — be consistent per section.
- Every numeric claim cites `recorded_live.json` / run id.
- Do not paste secrets.
- Keep vendor dumps out of the main narrative; link them.

## Next

Continue to [Phase 7 — Interactive artifact](07-interactive-artifact.md) for
normal mapping requests. Reuse the saved trace and the same important list;
do not re-derive facts in the UI layer or rerun the target solely to render it.
Honor an explicit data-only request and record unsupported targets or blockers.
After the navigator and delivery checks, run
[../checklists/definition-of-done.md](../checklists/definition-of-done.md).
