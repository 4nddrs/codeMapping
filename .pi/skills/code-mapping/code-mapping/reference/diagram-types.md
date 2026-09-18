# Diagram types

Optional figures that support the mapping document. Prefer accuracy over decoration.

| # | Diagram | Shows |
|---|---|---|
| 1 | Layered architecture | CLI/API → runtime → domain → tools/IO |
| 2 | Bootstrap | Ordered startup until ready |
| 3 | Orchestration / workflow | Authored graph, subgraphs, abort |
| 4 | Function flow | Critical-path functions on SUCCESS |
| 5 | Dataflow | How one hot payload moves (e.g. OBB, embedding) |
| 6 | Domain deep dive | Perception, planner, training step, etc. |
| 7 | Scheduler | Concurrency / frontier / event loop if relevant |
| 8 | Live values | Same as (4) or (5) annotated with trial numbers |

## Rules

- Caption every figure with the run id when it encodes live data.
- Use consistent colors for SUCCESS vs FAILURE edges.
- Do not invent boxes that did not run unless drawn dashed and labeled “not exercised.”
- Store PNGs (or SVG) under `docs/code_mapping/figures/` with numeric prefixes for stable ordering.
