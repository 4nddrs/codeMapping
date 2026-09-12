# Schema — `recorded_live.json`

Compact JSON derived from a **full SUCCESS (or FAILURE) trial** dump.

## Top-level object

| Key | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Human description of provenance (command, date, run path, caveats) |
| `command` | string | yes | Exact command |
| `trace` | string | yes | Relative path to run / trace directory |
| `result` | object | yes | Outcome metrics |
| `dag` \| `steps` | array | yes | Ordered executed nodes/steps |
| `nodes` \| `io` | object | recommended | Per-step I/O summaries |
| `assets` | object | optional | Index of heavy files |
| `gaps_refs` | string[] | optional | Gap ids from `GAPS.md` |

## `result` (recommended keys)

Adapt to the domain; keep what you can measure:

- `exit` / `success` / `reward`
- timing: wallclock, compute, control, steps, hz
- checkpoints / assertions
- cache indicators

## `dag` / `steps` item

| Key | Description |
|---|---|
| `name` | Stable step id |
| `node_type` / `kind` | tool, script, subgraph, noop, … |
| `script` | Implementing path if any |
| `status` | ok / failed / skipped / pending |
| `duration_ms` | if known |
| `error` | message or null |

## Per-node I/O

Under `nodes[name]` or parallel structure:

- `resolved_inputs` (summarized)
- `output` (summarized)
- `ctx.tool` / `subcalls` (optional)
- `assets` (relative paths)

## Invariants

- JSON must be free of secrets.
- Large ndarrays appear only as summary objects (see io-summarization).
- `source` must mention cache / substitution caveats if applicable.
