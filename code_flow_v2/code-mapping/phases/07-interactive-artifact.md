# Phase 7 — Interactive artifact and delivery

**Applicability:** Python targets only (see [Language limits](#language-limits)).
**Trigger:** complete this phase for normal code-mapping requests after the
evidence and documentation. Honor an explicit data-only, local-only, or
no-publish request; record an unsupported target or delivery blocker honestly.
A separate request for a website is not needed.

**Gate in:** phases 1–6 are closed or their waivers recorded; the trace matches
the brief's command and scope; phase 3's curated `important.txt` is available.
Capture may generate preliminary HTML earlier, but the final page must use
that curated list and the documented evidence.
**Gate out:** `call-tree.html` is rendered from the real run, added to the
shared menu, and verified through its local URL on port 8766. Complete the
configured menu push and deployment verification when authorized. Record
paths, verified URLs, and any unfinished delivery step under
`docs/code_mapping/runs/` and in the final handoff.

**The call tree is the only page this phase returns.** `mosaic.html` is
rendered alongside it and may be published as a secondary link *if the user
asks for the raw per-file coverage view* — it is not part of the deliverable.
And do **not** author an additional "explained" or "narrative" website out of
the mapping's artifacts: the durable prose deliverable is phase 6's
`MAPPING.md`, and a second hand-built site duplicates it, drifts from it, and
doubles the surface that has to stay true to the evidence. One command, one
canvas, one document. See [reference/anti-patterns.md](../reference/anti-patterns.md) #24.

## Purpose

Turn the same evidence phases 2–4 already gathered into the **same navigator**
used on the reference site: two standalone, zoomable HTML canvases — one
walking the real call tree from the entry point outward with arrows on every
call site, one showing every source file complete with executed lines lit up.
Both come from **one traced run**, not static analysis.

This phase does not re-derive facts. It renders `callgraph.json` +
`coverage.json` from a run of the brief's own `command`. See
[reference/sources-of-truth.md](../reference/sources-of-truth.md): the pages
rank with "dynamic coverage / call tree" — evidence of what ran, not a
replacement for `recorded_live.json`'s per-node values.

## The tool

[`../codetrace/`](../codetrace/) is a self-contained, portable tracer — copy
the whole folder into the target repo and run it. One dependency
(`coverage`), no build step, no server. Full contract, all flags, the value
right-click feature, and the exact rules for what is and isn't drawn are in
[`../codetrace/README.md`](../codetrace/README.md) — **read that file before
running it**; this page is the workflow around it, not a restatement.

Do not hand-write a `sys.setprofile` hook or a coverage wrapper for a Python
target — `codetrace` already does this generically (auto-detects source
roots, resolves `-m`, script, and console-script entry points via `runpy`,
walks past third-party frames, attributes threads to their `.start()` call).
If you find yourself writing one anyway, first check whether a `--entry` or
`--include` flag was the actual fix; see
[reference/dynamic-capture-python.md](../reference/dynamic-capture-python.md)
for why this is genuinely hard to get right from scratch.

## Steps

**Start with the saved trace.** If `callgraph.json`, `coverage.json`, and
`run.json` already exist for the brief's run, check their command, scope, and
source references, then go directly to **step 6 (`--rebuild`)**. Do not rerun
training or simulation solely to generate or publish the page.

If an existing capture uses a different value schema, first check for its
documented render command or adapter. Inspect representative primitives,
arrays, sample IDs, and execution contexts before using the stock rebuild.
Adapt the saved evidence at render time when needed, preserving entry/exit
timing, statistics scopes, omitted/truncated data, and distinct run phases.
Keep raw trace files unchanged and save the adapter and exact rebuild command
with the mapping. Verify the values in the rendered inspector; populated JSON
alone is insufficient. Only recapture when required evidence is actually
missing or cannot be recovered by rendering; document why and reconcile
phases 2–6 with that run before delivering.

1. **Install codetrace if needed.**
   ```bash
   cp -R /path/to/menuCodeMapping/code_flow_v2/code-mapping/codetrace <target-repo>/codetrace
   cd <target-repo>
   pip install coverage    # or: uv pip install coverage — see the warning below
   ```

2. **Never run it through an ad hoc environment overlay.** If the target uses
   `uv`, install `coverage` into the project's own venv and invoke with
   `uv run --no-sync`. Do **not** use `uv run --with coverage` (or any
   equivalent overlay-env mechanism in another tool). This was learned the
   hard way in the originating project: the overlay shadowed the `nvidia`
   packages already on the real venv's path, which made CUDA header discovery
   return `None` and broke a GPU motion planner deep in the call tree —
   nothing about coverage itself, purely an artifact of running in a
   different environment than normal. See
   [reference/anti-patterns.md](../reference/anti-patterns.md) #22 and
   [reference/dynamic-capture-python.md](../reference/dynamic-capture-python.md).

3. **Source the same environment the brief's command needs**, exactly as in
   [phases/02-capture.md](02-capture.md) — codetrace runs the target
   in-process, in your current shell, so anything the command needs (`.env`,
   `CUDA_VISIBLE_DEVICES`, etc.) must already be exported.

4. **Run it**, command after `--`, exactly as the user would type it:
   ```bash
   python codetrace/codetrace.py \
     --root . \
     --out docs/code_mapping/line_coverage/out \
     --include <dir-from-brief-in_scope> --include <another-one> \
     --title "<brief title>" \
     --brand "<repo name> · call tree with line coverage" \
     --important-file docs/code_mapping/important.txt \
     -- <brief command, unquoted, after the -->
   ```
   - `--include` should match the brief's **in scope** list, not the
     auto-detected default — auto-detect is a starting point (check the
     `watching …` line it prints), the brief is the source of truth for scope.
   - `--important-file` should point at the **same `important.txt` from
     phase 3** (see [Reconciling `important.txt`](#reconciling-importanttxt)
     below) so the ★ marks in the canvas match the curated critical path —
     don't maintain two lists.
   - During a phase-2 capture, omit `--important-file` if phase 3 is not done
     yet; add it with `--rebuild` (step 6) before the final phase-7 delivery.

5. **Check the outcome** against the brief's SUCCESS criteria (exit code,
   printed metric, etc. — codetrace prints `exit <code>` and draws the
   partial run even on a crash). If it doesn't match and a clean run matters,
   fix the environment and re-run; if you specifically want the FAILURE path
   evidenced, that's a legitimate use of this phase too — say so in `--label`
   and note it in the run inventory.

6. **Iterate without re-running.** Editing `--important-file`, `--entry`, or
   `--max-gap` does not require re-executing the target:
   ```bash
   python codetrace/codetrace.py --rebuild \
     --out docs/code_mapping/line_coverage/out \
     --important-file docs/code_mapping/important.txt
   ```

7. **Open `call-tree.html` locally once** to sanity
   check before publishing — confirm the entry point landed where expected
   (see [What ends up at the far left](../codetrace/README.md#what-ends-up-at-the-far-left)
   in the tool's README) and that `--include` didn't pull in vendored code.

   The same function will appear as **several cards** when it was entered from
   several call sites — that is deliberate, one card per call site, so each
   card's chips are the calls that entry really made. See
   [One card per call site](../codetrace/README.md#one-card-per-call-site-not-per-function).
   Amber back-edge counts rise after this change because shared leaves get a
   card per parent; check the count of *distinct* `from → to` name pairs, not
   the raw edge count.

   **Verify a UI claim in the UI.** Finding the data in `callgraph.json` or the
   page payload does not establish that the page *shows* it — a CSS specificity
   rule, a filter, or a swallowed regex can hide correct data. Before claiming a
   viewer behaviour works, drive the real page: load it headless, dispatch the
   actual `pointerdown`/`pointerup`/`contextmenu` sequence a user would, and read
   back the rendered DOM.

   ```bash
   # append a probe to a COPY of the page, then read the result out of <title>
   google-chrome --headless --disable-gpu --no-sandbox \
     --virtual-time-budget=45000 --window-size=1900,1100 \
     --dump-dom "file:///abs/path/probe.html" | grep -o '<title>PROBE[^<]*</title>'
   ```

   Two traps this catches: panels are **virtualised**, so a card that is not on
   screen is not in the DOM — scroll or navigate to it first, and never read
   `absent` as "missing from the page"; and `contextmenu` fires with
   `button === 0` for macOS Ctrl+click and touch long-press, so a handler that
   guards on `button === 2` alone will misbehave for real users.

8. **Deliver `call-tree.html` through the shared sessions menu.** Follow
   [`PUBLISHING.md`](../../PUBLISHING.md). Let `codetrace/menu_card.py` copy the
   page and derive the card's numbers from the trace. Give the page a real name
   through `--title`; keep its project slug and file path stable on updates.
   `mosaic.html` is published only if the user requests the coverage view.

   Add or update the card in `menuCodeMapping/index.html`, its README row,
   shelf count, and totals. Reuse the server on **localhost:8766** if it serves
   the correct checkout; otherwise start the documented local server. Open
   the menu in a browser, click the new card, and confirm the expected call
   tree loads and its controls work. A running server without this entry is
   not a delivered mapping.

   Once the local checks pass, commit and push the configured menu repository
   under existing user authorization, following `PUBLISHING.md`. Honor an
   explicit local-only/no-publish instruction. Verify the direct project URL
   on the configured deployment (for example, Netlify); a successful git push
   does not prove the site deployed. If configuration, credentials, or the
   deployment are unavailable, finish the local page and report that specific
   limitation without inventing a public URL or claiming the remote is live.

   If the shared menu is unavailable in another environment, deliver the
   standalone file or use an existing authorized hosting/artifact destination,
   and record this deviation. Do not create a second website.

9. **Record and return usable pointers.** Add the output path, direct local
   URL, verified deployed URL, and delivery status to
   `docs/code_mapping/runs/<run_id>.md` and link them from `MAPPING.md`.
   Return those verified URLs and the mapping document to the user. Clearly
   label a failed or pending deployment; do not inline HTML into the doc.

## When the command spawns processes

`codetrace` traces **the process it runs in**. Anything the command pushes into
a child process is invisible to it. Two cases come up constantly and both look
like "the tracer missed things" rather than what they are.

### A launcher that spawns workers (`torchrun`, `accelerate`, `mpirun`)

Wrapping the launcher traces the launcher and draws nothing of the real work.
Invert it: have the launcher start a small wrapper script **per rank**, and let
the wrapper run the target under `codetrace`. Trace one rank only — the profiler
costs wall time, and paying it on every rank skews collective operations.

```bash
#!/bin/bash
# trace_rank.sh — launched by: torchrun --no-python --nproc_per_node=2 bash trace_rank.sh
set -euo pipefail
ARGS=(train.py --flag value ...)
if [ "${LOCAL_RANK:-0}" = "0" ]; then
  exec python codetrace/codetrace.py --root . --out docs/code_mapping/line_coverage/out \
    --include mypkg --important-file docs/code_mapping/important.txt -- python "${ARGS[@]}"
else
  exec python "${ARGS[@]}"          # other ranks run bare
fi
```

Record "only rank N is traced" as a gap: rank-asymmetric branches (`if rank == 0`)
are drawn on the traced rank's side only.

### A dataloader with worker processes

This one is silent and costly. With PyTorch's `DataLoader(num_workers > 0)` the
**entire per-sample data pipeline runs in subprocesses** — dataset `__getitem__`,
file reads, decode, normalization, collation. The trace looks healthy, the page
renders, and a whole layer of the system is simply absent.

Set the worker count to **0 for the capture run** so the data path executes
in-process, and say so in the brief — it is a capture-time deviation, not a
convenience. Then record what that costs you: the multi-worker prefetch path is
now the thing that is unmapped.

Keeping *both* traces is worth it when the difference matters. The originating
project kept the workers>0 trace beside the workers=0 one; the diff between
their symbol sets **is** the evidence for the gap, and it is more convincing
than any prose.

The same reasoning applies to any out-of-process work: subprocess calls, RPC,
multiprocessing pools. If the command forks it, an in-process tracer will not
see it — decide whether to bring it in-process for the capture or to document
its absence, and never let it pass unnoticed.

## Reconciling `important.txt`

`codetrace --important-file` and this pack's phase-3
[`important.txt`](../schemas/important.schema.md) are **the same file** —
use one, not two. The tool's only hard requirement: a line is either a glob
pattern (`name`, `Class.method`, `path/glob.py:name`) or, if it starts with
`#` or is blank, ignored entirely. Continuation comment lines using this
pack's `why:` / `votes:` / `layer:` convention (see
[schemas/important.schema.md](../schemas/important.schema.md)) are exactly
the kind of line the tool already skips — no reformatting needed. Full
pattern grammar and how the ★ marks render: see
["Core-contribution functions"](../codetrace/README.md#core-contribution-functions)
in the tool's README.

## Honest gaps this phase introduces

Feed these into [phases/05-honest-gaps.md](05-honest-gaps.md) /
`GAPS.md` the same as any other capture method:

- **Import-time work is dropped by default.** Functions that only ran because
  a module was imported are excluded from the call tree (`--keep-imports` to
  include them). This is a deliberate scoping choice, not missing data — see
  the tool's ["What is and isn't drawn"](../codetrace/README.md#what-is-and-isnt-drawn).
- **Only your code is drawn.** Third-party and stdlib frames are walked past
  silently; a `via …` label on a chip means the call passed through such a
  frame before landing back in your code.
- **Values are sampled, not exhaustive.** The stock tracer records the first
  two calls of each function at exit; a mutated-in-place argument shows its
  final state. For another saved capture or adapter, describe its actual
  sampling policy and entry/exit timing instead. Do not imply a line-by-line
  timeline or coverage of calls that were never sampled.
- **One run is one path.** Branches this run didn't take are pink
  ("never ran"), not proof the branch is dead or unreachable.
- **Bundled back-edges understate the arriving edge count** until a circle is
  expanded, and the right-click list shows only the bundled call sites — a
  caller arriving by a forward arrow is drawn separately and not listed there.
- **Out-of-process work is absent.** Whatever the command pushed into a child
  process — dataloader workers, other ranks, subprocesses — did not reach the
  tracer. Name what was excluded and why.
- **Overhead.** Roughly 10–15% wall-time from the profiler hook, plus
  coverage's own cost. Fine for one capture run; don't leave it wrapping a
  production or benchmark invocation.

## Language limits

`codetrace` traces Python via `sys.setprofile` + `coverage.py`; there is no
equivalent tool bundled here for other languages. If the target isn't Python,
this phase is **not applicable** — say so explicitly in `GAPS.md` rather than
attempting a partial hand-rolled equivalent, unless the user specifically
asks for one built from scratch (then treat it as new tooling work, not this
phase).

## Anti-pattern reminder

Do not let this phase become the mapping. The pages are a **presentation
layer over Phase 2/4 evidence** — if `important.txt`, `recorded_live.json`,
and `GAPS.md` don't exist or are stale, fix those first
([reference/anti-patterns.md](../reference/anti-patterns.md) #1). A polished
navigator over uncurated data is not a finished mapping.

## Next

This is the final phase of the normal workflow. Return to
[checklists/definition-of-done.md](../checklists/definition-of-done.md).
