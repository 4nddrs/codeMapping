# Schema — Gaps document

File: `GAPS.md`.

## Required structure

1. Short intro (which run(s) the gaps apply to).
2. List of gap entries.
3. Acceptance log (who accepted which `blocks-claim` gaps).

## Gap entry fields

| Field | Description |
|---|---|
| `id` | Stable slug, e.g. `perception-cache-hit` |
| `severity` | `blocks-claim` \| `limits-detail` \| `cosmetic` |
| `summary` | One line |
| `detail` | What is missing or distorted |
| `evidence` | Run path, log, cache key, coverage absence |
| `affects` | Symbol / node ids |
| `status` | `open` \| `mitigated` \| `accepted` |
| `mitigation` | What would close it |

## Rules

- Every `blocks-claim` gap must be `mitigated` or `accepted` before calling the mapping “done.”
- Cards that touch a gap must list `gap_refs`.
