# Mapping document outline

Suggested filename: `docs/code_mapping/MAPPING.md` (or generate a PDF from the same structure).

---

# <Title>: Code Mapping

## 0. Metadata

- Command
- SUCCESS run id / path
- FAILURE run id / path (if any)
- Artifact index (brief, important, recorded_*, gaps)
- Navigator: verified direct local URL and deployed URL, or delivery limitation / user opt-out
- Status / date

## 1. What we are mapping

- Problem statement in one paragraph
- Exact command
- SUCCESS criteria and observed outcome
- In / out of scope

## 2. How to read this document

- Execution order = section order in the catalog
- How live values are summarized
- How failure edges are marked
- Where gaps are listed

## 3. Layered architecture

- Figure (optional)
- Short prose: CLI / API → runtime → domain → I/O boundaries

## 4. Bootstrap sequence

- Step list from process start to ready-to-run
- Figure (optional)

## 5. Orchestration / policy graph (if any)

- Authored graph summary
- Binding / dataflow notes
- Figure (optional)

## 6. Live trial summary

- Metrics table from `recorded_live.json`
- Checkpoint / assertion results
- Cache / RPC footnotes
- Pointers to video / assets

## 7. Function flow (SUCCESS)

- Figure of critical path
- Then **function cards** in order (one subsection each)

## 8. Deep dives (optional)

- Perception / model stack
- Scheduler / concurrency
- Geometry / planning
- Verification

## 9. Failure / abort path

- Evidenced vs static-only
- Cards for abort handlers
- Figure (optional)

## 10. Gaps and caveats

- Summarize `GAPS.md`; do not contradict it

## 11. Symbol index

| Symbol | Path | Card / section |
|---|---|---|
| | | |

## Appendix

- How artifacts were produced (commands for capture/compaction)
- Glossary
