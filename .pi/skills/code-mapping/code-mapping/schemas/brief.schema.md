# Schema — Project brief

File: `BRIEF.md` (Markdown). Human- and agent-readable contract for one mapping.

## Required fields

| Field | Description |
|---|---|
| `title` | Short name of the mapping |
| `command` | Exact shell command under study |
| `entrypoint` | Language entry (module:function or CLI script) if known |
| `success_criteria` | How SUCCESS is decided |
| `artifact_root` | e.g. `docs/code_mapping/` |
| `in_scope` | Packages / dirs / subsystems included |
| `out_of_scope` | Explicit exclusions |
| `status` | `draft` \| `frozen` |

## Recommended fields

| Field | Description |
|---|---|
| `failure_scenario` | Command or condition for abort-path evidence |
| `env_vars` | Names (not secret values) required to run |
| `run_success` | Path to SUCCESS run directory or log |
| `run_failure` | Path to FAILURE run if any |
| `orchestration_artifact` | Workflow JSON / pipeline YAML path if any |
| `notes` | Caches, hardware, flaky deps |
| `owners` | Who can approve freezes |

## Validation

- `command` must be copy-pasteable.
- `success_criteria` must be checkable from artifacts.
- When `status: frozen`, later phases may not change scope without bumping status back to `draft` and noting why.
