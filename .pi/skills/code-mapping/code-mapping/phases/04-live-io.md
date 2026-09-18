# Phase 4 — Live I/O

**Gate in:** critical-path list exists.<br>
**Gate out:** `recorded_live.json` (and optional `recorded_values.json`) with summarization rules applied; no secrets.

## Purpose

Attach **measured** inputs/outputs to critical-path steps so the mapping is not type-only.

## Prefer trial dumps

If the runtime already writes per-node or per-span data (e.g. `node_data/`, traces, OpenTelemetry, custom JSON):

1. Compact it into `recorded_live.json` using [../reference/io-summarization.md](../reference/io-summarization.md).
2. Keep pointers to heavy assets (images, point clouds, videos) instead of inlining pixels.
3. Preserve node/step names exactly as in the trial when possible.

## Supplemental capture

When the full trial is too heavy or skips a subsystem, a **narrow** capture script may record authentic tool values (observations, poses, world snapshots) without re-running the entire stack.

Rules:

- Label the source clearly in the JSON `source` field.
- Never present ground-truth substitutes as perception outputs without saying so.
- Keep supplemental capture in `recorded_values.json` separate from the full-trial `recorded_live.json`.

## What to record per step (minimum)

- Step / node / function id
- Status / duration if known
- Resolved inputs (summarized)
- Outputs (summarized)
- Nested tool / RPC subcalls if present in the dump
- Asset paths (relative to run dir)

## Summarization (mandatory for large payloads)

Follow [../reference/io-summarization.md](../reference/io-summarization.md):

- Scalars / small structs: keep (rounded floats OK).
- Large arrays/tensors: `shape`, `dtype`, `min`/`max`/`mean`, `firstN`, optional centroid / nonzero stats.
- Long lists of dicts: `len` + first (and maybe second) fully summarized.
- Strings: truncate only if huge; note original length.

## Schema

- [../schemas/recorded-live.schema.md](../schemas/recorded-live.schema.md)
- [../templates/recorded-live.template.json](../templates/recorded-live.template.json)
- [../schemas/recorded-values.schema.md](../schemas/recorded-values.schema.md)

## Sanity checks

- SUCCESS metrics in JSON match the run note.
- Perception/cache/RPC footnotes match reality.
- No API keys, tokens, home directories with credentials.

## Next

Phase 5 — Honest gaps.
