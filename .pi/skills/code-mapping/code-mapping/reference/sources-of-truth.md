# Sources of truth (precedence)

When sources disagree, higher wins for **factual claims about the trial**.

1. **Raw SUCCESS/FAILURE run directory** (traces, node dumps, logs, metrics written by the program)
2. **`recorded_live.json`** (compact view of (1); if it disagrees with (1), fix the compact file)
3. **`recorded_values.json`** — only for what its `source` says it measured; never overrides (1) for full-trial perception/etc.
4. **Dynamic coverage / call tree** — what code ran; not a substitute for I/O values. Includes [phase 7's](../phases/07-interactive-artifact.md) `coverage.json` / `callgraph.json` and the rendered `call-tree.html` / `mosaic.html` — the pages are a **rendering** of this rank, not a higher one; if a page and the raw JSON disagree, regenerate the page (`--rebuild`), don't hand-edit it.
5. **`important.txt`** — curated narrative set; may omit executed noise; must not claim unexecuted code ran. Shared verbatim with phase 7's `--important-file` — one file, see [phases/07-interactive-artifact.md](../phases/07-interactive-artifact.md#reconciling-importanttxt).
6. **Orchestration artifacts** (workflow JSON, etc.) — intended structure; may include nodes not taken on this trial
7. **Mapping document / PDF** — must cite (2)/(3); never invent
8. **Product docs / READMEs** — intent and how-to; not trial evidence

## Editing rule

If you change a number in the mapping doc, update `recorded_*.json` first (or regenerate it from the run), then the doc.
