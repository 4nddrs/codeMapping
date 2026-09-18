# Objective — Code Mapping from a Live Run

## One-sentence goal

Walk the **real execution path** of one command, **function by function**, with the **values that actually flowed** through each call — and keep the **control-flow graph including failure** — so a reader can understand the system without re-deriving it from source alone.

## What “code mapping” means

1. **One command** (or one clearly named entrypoint + args) is the unit of study.
2. That command is executed at least once to produce a **SUCCESS** trial (and ideally one **FAILURE** trial for abort paths).
3. For **every function on the critical path**, record:
   - file path
   - qualified symbol name
   - line range
   - the **full function** (or a faithful extract), not only a snippet
   - a short explanation of **why it exists on this path**
   - **actual inputs and outputs** from the live trial (not types alone)
4. Keep **edges**: next-on-success and next-on-failure / abort, so the reader can walk forward and backward.
5. State **honest gaps**: caches, out-of-process RPC, code not exercised, truncated arrays, missing traces.

## Two layers (when the project has both)

Many systems have:

| Layer | Meaning |
|---|---|
| **Orchestration / policy graph** | Declared workflow, DAG, pipeline stages, skill subgraphs |
| **Implementation / function flow** | CLI → runtime → tools → scripts that actually ran |

Map **both** when both exist. Do not confuse “nodes in a workflow JSON” with “Python functions that executed.”

## Definition of done (summary)

A mapping is done when:

- The brief is filled and frozen.
- A SUCCESS trial is identified and referenced by path / id.
- The critical-path list (`important`) is curated with “why” notes.
- Live I/O is captured and summarized (arrays as stats + asset pointers).
- Failure path is documented or explicitly marked N/A with reason.
- Gaps are listed; nothing invented is presented as measured.
- A durable mapping document (Markdown and/or PDF) exists that a stranger can follow Next/Back style.
- For a supported Python target, the call-tree navigator is rendered from the
  same run, linked from the shared menu, and verified at its local URL.
- The configured menu is pushed and its deployed page verified when authorized;
  the final handoff includes actual usable URLs and the mapping document.

The navigator is the normal final presentation of the evidence. An explicit
data-only or no-publish request changes the delivery scope. Unsupported
languages, missing trace data, rendering errors, and deployment blockers must
be recorded honestly; an unverified URL is not a finished delivery.

## Non-goals

- Replacing unit tests or coverage reports.
- Static call graphs without a run.
- Exhaustive documentation of unused modules.
- Pretty diagrams without numbers from the trial.
