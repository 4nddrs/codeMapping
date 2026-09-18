# Example brief — GaP Libero quickstart (worked)

This is the **canonical example** that motivated this skill pack. Copy the *shape*, not the GaP-specific details, into other projects.

- **title:** Graph-as-Policy — Libero quickstart code mapping
- **status:** frozen (historical example)
- **artifact_root:** `docs/code_mapping/`
- **date_opened:** 2026-09-03

## Command under study

```bash
uv run gap run examples/libero_quickstart/graph --sim libero_object_all_variance/0
```

## Entrypoint

- CLI: `gap` → `gap.cli:main` → `gap run` → `gap.runtime.execute.execute`
- Workflow: `examples/libero_quickstart/graph/workflow.json`

## SUCCESS criteria

- Workflow exit success
- Sim `check_success` / reward ≈ 1.0
- Example SUCCESS trial: `outputs/run_20260903_102839/` (reward 1.0, wallclock ~60s)

## FAILURE scenario

- Cold-cache / auth failure path documented via a separate failing run (e.g. perception 401) for abort edges
- Workflow `on_error` → `abort` (open gripper, go home)

## Environment (names only)

| Variable | Purpose |
|---|---|
| `MUJOCO_GL` | Headless EGL rendering (`egl`) |
| `OPENROUTER_API_KEY` / `GAP_VLM_*` | VLM provider |
| `HF_TOKEN` | Gated SAM3 weights |
| `GAP_PERCEPTION_CACHE` | May short-circuit DINO/VLM/SAM3 |

## Orchestration artifact

- `examples/libero_quickstart/graph/workflow.json`
- Subgraphs: `target_sg` → `container_sg` → `grasp_sg` → `transport_sg` → `done`, with `abort` on failure

## In scope

- CLI → connector → LIBERO env → executor → skill scripts → robot tools → teardown
- Checkpoints (`grasp_sg`)
- Failure / abort path

## Out of scope

- `gap generate`, benchmark harness, real-robot connectors, viz server internals

## Known complications

- **Perception cache HIT** on the SUCCESS trial: perceive scripts returned real outputs, but DINO/VLM/SAM3 were not re-invoked → documented as gaps
- Geometry tools may run **out-of-process (RPC)** → absent from in-process coverage lists
- Large RGB/depth/clouds stored as stats + asset paths, not full dumps

## Two layers

| Layer | Artifact |
|---|---|
| Policy / workflow graph | `workflow.json` |
| Implementation / function flow | `important.txt` + coverage/call tree + function cards |

## Mapping products in this repo

- Compact live I/O: `docs/code_mapping/recorded_live.json`
- Supplemental values: `docs/code_mapping/recorded_values.json`
- Critical path: `docs/code_mapping/line_coverage/important.txt`
- Long-form PDF: `docs/GaPCodeMapping.pdf`
- Capture helpers: `parse_live_trace.py`, `capture_values.py`, `diagrams.py`, `build_pdf.py`

This historical example lists the evidence and documentation. New mappings
also finish phase 7: render the call-tree navigator from the same trace, add it
to the shared menu, and return verified delivery URLs unless the user opts out.
