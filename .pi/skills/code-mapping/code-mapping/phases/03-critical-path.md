# Phase 3 — Critical path

**Gate in:** run inventory exists.<br>
**Gate out:** curated `important.txt` (or equivalent) with **why** notes; draft next/failure edges.

## Purpose

Turn a noisy executed-function list into the **story the reader should walk**.

## Inputs

- Dynamic call tree / coverage (if available)
- Orchestration graph (workflow JSON, pipeline YAML, state machine) if any
- Domain docs / paper claims (what the authors say matters)
- User priorities

## Method

1. Extract candidate functions from the dynamic trace (executed only).
2. Cluster by stage: bootstrap → orchestration → domain steps → teardown.
3. Keep functions that are **load-bearing** for the claim under study:
   - entrypoints and dispatch
   - scheduler / executor
   - domain scripts that implement the task
   - verification / checkpoints
   - failure handlers
4. Drop or demote:
   - pure import side effects
   - trivial getters unless they define a contract boundary
   - huge third-party internals (summarize as a boundary instead)
5. For each kept symbol, write a **why** (1–3 sentences): why it is on this path for *this* command.
6. Optionally record votes / confidence if multiple readers or passes agree.

## Output format

Use [../templates/important.template.txt](../templates/important.template.txt) and [../schemas/important.schema.md](../schemas/important.schema.md).

Typical line:

```text
path/to/file.py:ClassName.method
#     why: …
```

Globs are allowed when a whole class surface matters (`WorkflowExecutor.*`).

## Edges

While curating, sketch:

- **next** — primary SUCCESS successor(s)
- **on_failure** — abort / retry / fallback targets

Store edges later in function cards; a rough adjacency list in comments is fine at this stage.

## Two-layer reminder

If the project has an authored workflow graph **and** code functions:

- List workflow nodes separately (names from the graph).
- Map graph nodes → implementing functions / scripts.
- Do not pretend they are the same ID space.

## Paper innovation (optional)

When the brief studies a contribution, such as a paper's method or a mechanism
the repository adds, also record **which lines implement it** in `innovation.json`
([schema](../schemas/innovation.schema.md) ·
[template](../templates/innovation.template.json)). Phase 7 draws those cards
with a green frame. This is a different question from the critical path: most
load-bearing functions are standard machinery, and some innovation lines sit
inside long generic functions.

1. Write each claim from the paper's method section or the README as one sentence.
2. Diff the executed functions against the code the project builds on, such as
   upstream repositories or earlier work by the same authors. Read both; don't
   rely on memory. Lines added or changed for a claim are `core`.
3. For each candidate line, ask: would it exist, or behave the same, without the
   contribution, for example in the baseline or pooled configuration? If yes,
   it is generic. Leave it out, or mark it `supporting` only where the new data
   or mechanism takes effect or becomes affordable.
4. Keep ranges tight, on statement boundaries. List each function once, with
   all of its ranges. Write a `what` for each range, a `provenance` for each
   function, and a `text` (the stripped first line), so stale line numbers fail
   at render time.
5. Try to refute each range before keeping it. Independent readers, or one
   skeptic pass per function, catch most over-marking. Record rejected
   candidates in `review.excluded`.

## Next

Phase 4 — Live I/O.
