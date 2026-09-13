# Phase 2 — Capture

**Gate in:** brief exists.<br>
**Gate out:** SUCCESS trial located (or freshly run); raw evidence indexed; trace/coverage data available for the default navigator, or a limitation recorded.

## Purpose

Obtain **machine evidence** from a real execution. Capture is not documentation yet.

## Prefer existing runs

If a SUCCESS trial already exists and matches the brief command:

1. Record its path (e.g. `outputs/run_YYYYMMDD_HHMMSS/`).
2. Inventory what it contains: logs, DAG/trace JSON, per-node dumps, videos, checkpoints, metrics.
3. Do **not** re-run only to regenerate identical data unless the user wants a fresh trial.

## If you must run

1. Load env from the project’s documented mechanism (`.env`, direnv, etc.).
2. Run the **exact** brief command.
3. Confirm SUCCESS criteria.
4. Optionally run a FAILURE scenario for abort-path evidence.
5. Store pointers under `docs/code_mapping/runs/` (notes + relative paths), not copies of huge binaries unless needed.

## Coverage / call tree

For Python targets, preserve `callgraph.json`, `coverage.json`, and `run.json`
from the same run so phase 7 can render the default navigator without another
training or simulation run. Read phase 7's capture guidance and the bundled
`codetrace/README.md` before starting a fresh capture. If an existing trial lacks
necessary trace data, document the gap and assess whether a scoped recapture is
needed; do not silently substitute a different run. Other languages and explicit
data-only requests may use their own evidence without this Python navigator.

Options used in the originating project:

- Project `codetrace`-style one-shot tracer (coverage + call tree HTML + optional value samples).
- `coverage.py` JSON export + a curated important-file filter.

Rules:

- Prefer **one real run** over static analysis.
- Record include roots (`--include`) so vendored noise is limited.
- Use the complete current `codetrace/` bundle, including `_boundaries.py`.
  Fresh captures record project line events per calling context, exact instance
  edges, and direct observed dependency boundaries. Keep the boundary metadata
  and unavailable-value reasons with the raw evidence. The bundled runner uses
  coverage's Python tracer (`timid=True`) so its coverage hook composes with
  context line capture; adapters must preserve this configuration.
- Audit capture errors, dropped boundary records and unfinished samples. Check
  representative actual library/module calls before launching an expensive
  command suite. Boundary source is reference material, not internal execution
  evidence; native values unavailable from the profiler must stay unavailable.
- Save outputs under something like `docs/code_mapping/line_coverage/` or `codetrace_out/`, and link them from the brief / runs note.

## `exit 0` is not evidence the right run happened

A command can succeed and still not be the run your brief describes. Check what
the run *did*, not only that it finished — read the log for the lines that prove
the intended work happened, and reconcile them against the call counts in the
trace.

The failure that motivated this: a fine-tuning capture launched with
`--max-steps 2` exited 0 in ~20 minutes, and every forward-path function
(`compute_loss`, `RLDX.forward`, `MSAT.forward`, `JointBase._forward_inner`)
showed `×1` in the call tree. The log said why:

```
[i] Resuming from checkpoint outputs/train_map_traced/debug/checkpoint-4
[i] Current global step: 4
```

HF Trainer auto-resumes from the newest checkpoint in `--output-dir`. A leftover
checkpoint from an earlier trial made the run continue that training and take a
single optimizer step, from a checkpoint the brief never mentions. Nothing
failed; the artifact was simply describing a different run.

Reconcile these before trusting a capture:

- **Steps / iterations actually performed** vs the flag you passed
  (`0/2` in a progress bar, or a jump to `5it`, is not `2/2`).
- **Starting weights** — a "resuming from" or "loading checkpoint" line means the
  run did not start where the brief says it did.
- **Call counts of the hot path** vs how many iterations you asked for. `N`
  optimizer steps should give the forward path `×N`. A mismatch is a fact about
  the run, so chase it to a log line before writing it up or explaining it away
  as a tracer artifact.
- **Output directory state** — for anything that checkpoints, trace into a
  directory that is empty, and make the capture script refuse to start when it
  is not:

  ```bash
  OUTPUT_DIR=./outputs/<repo>_traced_clean
  if compgen -G "$OUTPUT_DIR/*/checkpoint-*" > /dev/null 2>&1; then
    echo "refusing to trace: $OUTPUT_DIR holds a checkpoint (Trainer would resume)" >&2
    exit 1
  fi
  ```

Keep the misleading trace rather than deleting it — it is evidence, and the
contrast between the two runs is what makes the gap legible. Park it beside the
good one (`line_coverage/out_resumed_stale/`) and record it in
[GAPS.md](../schemas/gaps.schema.md).

## Inventory checklist

Create or update `docs/code_mapping/runs/<run_id>.md`:

- Command (verbatim)
- Timestamp / run directory
- Outcome (SUCCESS/FAILURE + metrics)
- Key files inside the run (trace, node_data, video, logs)
- Env flags that affected behavior (cache on/off, renderer, etc.) — **names and values that are not secrets**
- Known anomalies during the run

## Do not

- Commit secrets.
- Treat import-time-only functions as critical path yet (filter later).
- Start writing the full mapping prose in this phase.

## Next

Phase 3 — Critical path.
