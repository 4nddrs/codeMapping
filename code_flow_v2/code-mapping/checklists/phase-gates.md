# Phase gates

Tick when leaving each phase. Do not start phase *N+1* documentation work until gate *N* is closed.

## Gate 1 — Scope → Capture

- [ ] Brief filled
- [ ] Command copy-pasteable
- [ ] Artifact root agreed
- [ ] Open questions listed or resolved

## Gate 2 — Capture → Critical path

- [ ] SUCCESS run identified or executed
- [ ] Run inventory written
- [ ] Trace/coverage artifacts linked

## Gate 3 — Critical path → Live I/O

- [ ] Important list drafted with why notes
- [ ] User or owner OK on inclusion set (or time-boxed agent pass noted)
- [ ] Rough SUCCESS order agreed

## Gate 4 — Live I/O → Gaps

- [ ] `recorded_live.json` written
- [ ] Summarization rules applied
- [ ] Optional `recorded_values.json` labeled if used

## Gate 5 — Gaps → Documentation

- [ ] `GAPS.md` written
- [ ] `blocks-claim` items dispositioned
- [ ] Cards know their `gap_refs`

## Gate 6 — Documentation → Interactive artifact

- [ ] Mapping doc assembled from the frozen evidence
- [ ] Phase 1–6 checks complete or waivers recorded

## Gate 7 — Interactive artifact → Delivered

Part of the normal workflow after gate 6. Record an explicit data-only or
no-publish choice, unsupported language, or blocker rather than silently
skipping delivery. Capture-time checks below apply to the saved run too.

- [ ] Matching saved trace reused with `--rebuild`, or need for a new capture documented
- [ ] `codetrace/` available; `coverage` in the project's own environment if a fresh capture is required
- [ ] Traced run's outcome checked against the brief's SUCCESS criteria
- [ ] `--include` matches the brief's in-scope list (not left at auto-detect without checking)
- [ ] `--important-file` points at this mapping's curated `important.txt`
- [ ] If the command spawns processes (launcher, dataloader workers, subprocesses):
      the tracer wraps the work, and out-of-process layers are either brought
      in-process for the capture or recorded as unmapped
- [ ] Page inspected in a browser; entry point and relevant UI controls verified
- [ ] Page has a real project title
- [ ] `call-tree.html` copied to `menuCodeMapping/projects/<slug>/`; card and
      README row added or updated; shelf count and totals updated
      (`codetrace/menu_card.py` derives values — see `PUBLISHING.md`)
- [ ] Menu on localhost:8766 opened and new card clicked successfully
- [ ] Authorized menu changes committed and pushed to configured `origin/main`
      after local verification, or precise local-only/blocker status recorded
- [ ] Configured deployed menu and direct project URL verified, or the failed /
      unavailable deployment clearly reported (a push alone is not proof)
- [ ] Output path, verified local/deployed URLs, and delivery status recorded
      under `runs/`, linked from `MAPPING.md`, and included in the final handoff
- [ ] Mosaic published only if requested; no second hand-authored site
- [ ] Phase-specific gaps recorded, including bundling and any out-of-process exclusion
- [ ] Full definition-of-done checklist run
