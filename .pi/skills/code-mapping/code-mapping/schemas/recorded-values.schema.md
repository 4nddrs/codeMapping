# Schema — `recorded_values.json`

Optional **supplemental** capture when the full trial dump is incomplete or too heavy for some subsystems.

## Intent

Hold authentic values from a narrower probe (e.g. connector reset + pure geometry), clearly labeled so they are not confused with full-trial perception outputs.

## Top-level object

| Key | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Must state what was and was **not** run |
| `suite` / `scenario` | string | recommended | Domain scenario id |
| `tools` | object | recommended | `tool.name → {inputs, output}` |
| `scripts` | object | optional | Pure functions exercised with constructed inputs |
| `world` | object | optional | Ground-truth snapshot summaries |
| `notes` | string | optional | Substitutions (e.g. GT AABB → OBB) |

## Rules

- Always distinguishable from `recorded_live.json`.
- Mapping docs must cite which file a number came from.
- Same summarization rules as live I/O.
