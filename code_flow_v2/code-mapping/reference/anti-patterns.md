# Anti-patterns

Avoid these; they destroy trust in a mapping.

## Process

1. **UI first** — treating [phase 7's](../phases/07-interactive-artifact.md) navigator as finished before the evidence, `recorded_live.json`, `important.txt`, gaps, and documentation are ready. The navigator is the normal final phase; a polished page does not replace curation.
2. **Whole-repo mapping** — no single command, no SUCCESS trial.
3. **Static-only graphs** — call graphs from imports without execution evidence.
4. **Skipping gaps** — cache hits presented as full pipeline exercise.
5. **Phase skipping** — writing catalog prose during capture.
6. **Silent scope creep** — adding subsystems without updating the brief.
7. **`exit 0` read as "the right run happened"** — a capture that finishes cleanly can still be a different run than the brief describes (a trainer resuming from a leftover checkpoint takes one step instead of the two you asked for). Reconcile the log's step count and starting weights, and the hot path's call counts, against the flags you passed — see [`exit 0` is not evidence](../phases/02-capture.md#exit-0-is-not-evidence-the-right-run-happened).
8. **Explaining a count mismatch as a tool artifact** — when the trace disagrees with the command (`×1` where you expected `×2`), the default assumption is that the trace is right and the run was different. Chase it to a log line before blaming the tracer or the renderer.

## Data

9. **Invented numbers** — “typical” poses or fake rewards.
10. **Type-only cards** — signatures without recorded values when values exist.
11. **Raw dumps** — multi‑MB arrays inlined into JSON or Markdown.
12. **Secret leakage** — keys in JSON, screenshots of `.env`, tokens in logs pasted into docs.
13. **Substitution without label** — ground-truth geometry labeled as perception output.
14. **Orphan metrics** — numbers in the PDF that cannot be found in `recorded_*.json`.

## Curation

15. **Important = everything executed** — including stdlib and import noise.
16. **No why** — symbol lists without rationale.
17. **Confusing layers** — treating workflow node names as Python functions interchangeable IDs without a mapping table.
18. **Failure amnesia** — SUCCESS-only story when abort edges exist in the product claim.

## Documentation

19. **Architecture essay without a walk** — pretty layers, no Next/Back path.
20. **Copying third-party internals** — pages of library source instead of a boundary card.
21. **Contradicting GAPS.md** — narrative claims the gap file denies.

## Capture tooling

22. **Ad hoc environment overlays around a tracer** — `uv run --with <pkg>` or
    any equivalent that builds a temporary dependency overlay for the traced
    process. It can shadow packages already correctly installed in the
    project's real environment (native/compiled ones doing their own runtime
    path discovery are especially vulnerable) and produce a failure that
    looks like a bug in the traced code but is really the overlay. Install
    the tracer's dependency into the project's own environment instead. See
    [reference/dynamic-capture-python.md](dynamic-capture-python.md) #6.
23. **Two runs standing in for one** — running coverage and a call-graph
    profiler as separate invocations of a possibly-nondeterministic command
    and treating the results as describing the same execution. Capture both
    signals from one run of the process.
24. **A second website beside the call tree** — hand-authoring an "explained"
    or "narrative" site out of the mapping's artifacts in addition to
    [phase 7's](../phases/07-interactive-artifact.md) `call-tree.html`. The
    prose deliverable already exists: phase 6's `MAPPING.md`. A second site
    duplicates it, drifts from it the moment either changes, and doubles the
    surface that has to stay true to the evidence. One command, one canvas,
    one document. (If a page really is wanted *instead of* the Markdown,
    generate it from the same artifacts so it cannot drift — never write its
    numbers by hand.)
25. **Tracing the launcher instead of the work** — wrapping `torchrun`,
    `accelerate`, `mpirun` or any process spawner in the tracer. It traces the
    spawner and draws nothing of the command. Invert it: the launcher starts a
    per-rank wrapper, the wrapper runs the target under the tracer. See
    [phases/07-interactive-artifact.md](../phases/07-interactive-artifact.md#when-the-command-spawns-processes).
26. **Silently losing a whole layer to worker processes** — capturing with a
    dataloader (or pool, or subprocess) whose workers run out-of-process, and
    presenting the resulting trace as the command's full path. The page looks
    complete; the data pipeline is simply not in it. Set workers to 0 for the
    capture, declare it in the brief, and record the multi-worker path as the
    thing now unmapped.
27. **Stopping before the flow is viewable** — calling a normal mapping complete
    after saving trace JSON or Markdown while its navigator or shared-menu link
    is missing. Rebuild the saved trace, verify localhost:8766, and finish the
    authorized push/deployment workflow; record explicit opt-outs or blockers.
