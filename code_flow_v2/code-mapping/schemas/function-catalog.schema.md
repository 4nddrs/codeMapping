# Schema — Function catalog card

One card per critical-path symbol. May live as sections in `MAPPING.md` / `function_catalog.md` or as separate files.

## Required fields

| Field | Description |
|---|---|
| `id` | Stable slug (often symbol or workflow node name) |
| `path` | Repo-relative file path |
| `symbol` | Qualified name |
| `lines` | `[start, end]` inclusive if known |
| `why` | 1–3 sentences: role on **this** path |
| `code` | Full function text or faithful extract |
| `inputs` | Table or JSON — types **and** recorded values when available |
| `outputs` | Same |
| `next` | SUCCESS successors (ids) |
| `on_failure` | Failure successors (ids) or `none` |

## Recommended fields

| Field | Description |
|---|---|
| `layer` | bootstrap / orchestrator / domain / verify / teardown / failure |
| `workflow_node` | Orchestration node name if different from symbol |
| `duration_ms` | From trial |
| `recorded_ref` | Pointer into `recorded_live.json` |
| `gap_refs` | Ids from `GAPS.md` |
| `see_also` | Related cards |

## Ordering

Catalog order = **execution order on the SUCCESS path**, with failure cards grouped at the end or reachable only via `on_failure`.
