# Phase 5 — Honest gaps

**Gate in:** live I/O artifacts exist.<br>
**Gate out:** `GAPS.md` lists every material limitation; function cards that touch gaps reference them.

## Purpose

Prevent false confidence. A mapping that hides caches or missing traces is worse than no mapping.

## Hunt for gaps

Ask, for each critical-path item:

1. **Was this code actually executed** on the SUCCESS trial, or only imported / only present in source?
2. **Did a cache short-circuit** work (LLM, perception, dataset, memoization)?
3. **Did work happen out-of-process** (RPC, subprocess, remote worker) so it is absent from in-process coverage?
4. **Are values substituted** (ground-truth AABB instead of perceived OBB, mocks, fixtures)?
5. **Is the FAILURE path evidenced** by a real failing trial, or only by static edges?
6. **Are arrays truncated** such that a reader might misread them as complete?
7. **Are third-party internals elided** at a boundary (state the boundary)?

## Output

Fill [../templates/gaps.template.md](../templates/gaps.template.md) → `docs/code_mapping/GAPS.md`.

Each gap entry:

- id (stable slug)
- severity (`blocks-claim` | `limits-detail` | `cosmetic`)
- what is missing / distorted
- evidence (run id, log line, cache key)
- mitigation (cold cache re-run, separate RPC trace, etc.) or `accepted`

## Policy

- Anything that would change a paper-style claim → `blocks-claim` until mitigated or explicitly accepted by the user.
- Never silently upgrade a cache-hit trial into “full pipeline exercised.”

## Next

Phase 6 — Documentation.
