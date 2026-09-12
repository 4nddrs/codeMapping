# Definition of done — Code Mapping

A mapping may be called **complete** only when all boxes are checked or explicitly waived with reason in `GAPS.md` / brief.

## Scope

- [ ] `BRIEF.md` exists with exact command and SUCCESS criteria
- [ ] Brief `status` is `frozen` (or waiver recorded)
- [ ] In / out of scope lists are non-empty and specific

## Capture

- [ ] SUCCESS trial path recorded and still readable
- [ ] Run inventory note lists key files (trace, logs, metrics, assets)
- [ ] Dynamic coverage / call-tree produced **or** waiver explaining why not
- [ ] Optional FAILURE trial recorded **or** failure path marked static-only in gaps

## Critical path

- [ ] `important.txt` (or equivalent) curated with **why** on every entry
- [ ] Order matches SUCCESS execution story
- [ ] Orchestration nodes mapped to implementing functions when both exist

## Live I/O

- [ ] `recorded_live.json` exists, cites command + trace path
- [ ] Large arrays summarized (no raw megabyte dumps in JSON)
- [ ] Numbers used in docs cite this file or `recorded_values.json`
- [ ] No secrets in any artifact

## Gaps

- [ ] `GAPS.md` exists
- [ ] Every `blocks-claim` gap is `mitigated` or `accepted`
- [ ] Cache / RPC / substitution issues called out if present

## Documentation

- [ ] `MAPPING.md` and/or PDF follows the outline (metadata → catalog → failure → gaps → index)
- [ ] Function cards cover the important list (or note deliberate omissions)
- [ ] Failure path section exists
- [ ] Symbol index exists

## Interactive artifact and delivery (default)

See [phases/07-interactive-artifact.md](../phases/07-interactive-artifact.md).
Complete this section for normal mapping requests. Record explicit user
opt-outs, unsupported targets, or delivery blockers with the completed local
work; do not describe an unavailable page or deployment as finished.

- [ ] `call-tree.html` rendered from the brief's real run; matching saved trace
      reused without rerunning the target unless recapture was necessary
- [ ] `--important-file` used the same curated `important.txt` as phase 3
- [ ] Exactly one navigator delivered; mosaic only if requested, no second website
- [ ] Page and card added/updated in the shared menu with accurate totals
- [ ] Local menu on port 8766 opened in a browser; new card opens the correct page
- [ ] Served-page stage/search navigation and value-inspector gestures/pagination
      checked against saved samples; shapes, statistics scopes, and contexts
      agree with the evidence (see [browser checks](../../PUBLISHING.md#browser-acceptance-checks))
- [ ] Authorized menu changes committed and pushed to configured `origin/main`,
      or explicit local-only choice / push blocker recorded (see `PUBLISHING.md`)
- [ ] Deployed menu and direct page verified at the configured URL, or deployment
      limitation clearly recorded; git push is not counted as site verification
- [ ] Run inventory and `MAPPING.md` contain output paths, verified delivery URLs,
      and the delivery status; final response includes usable direct links
- [ ] Delivery record retains render command, browser results, and pushed commit;
      brief/checklist/gaps reflect completed delivery without stale exclusions
- [ ] Phase-specific gaps recorded: import-time drop, sampled values, single-run
      coverage, bundled back-edges, and anything that ran out-of-process

## Optional extensions

- Mosaic / raw per-file coverage view, if requested
- Extra diagrams or exhaustive third-party internals, if requested
- Re-running cold-cache full stack, if needed to resolve a `blocks-claim` gap

Do not build a second hand-authored website beside the call tree; `MAPPING.md`
is the prose deliverable.
