# Artifact layout

Recommended tree inside a target repository:

```
docs/code_mapping/
  BRIEF.md
  GAPS.md
  important.txt
  recorded_live.json
  recorded_values.json          # optional
  function_catalog.md           # or fold into MAPPING.md
  MAPPING.md
  figures/
    01_architecture.png
    02_bootstrap.png
    03_workflow.png
    04_function_flow.png
    05_dataflow.png
    06_<domain_deep_dive>.png
    07_scheduler.png            # if relevant
    08_live_values.png          # annotated with trial numbers
  runs/
    SUCCESS_<id>.md             # pointer + inventory (not a full copy)
    FAILURE_<id>.md
  line_coverage/                # Python trace data for phases 2 and 7
    codetrace/                  # copied from skillsCodeMapping/code-mapping/codetrace/
    out/                        # codetrace --out: call tree, optional mosaic + data
      call-tree.html
      mosaic.html
      callgraph.json
      coverage.json
      payload_call_tree.json
      payload_mosaic.json
      run.json
      run.log
    coverage.json                       # if captured separately from phase 7 (e.g. coverage only, no call tree)
    callgraph.json
    important.txt               # may symlink to ../important.txt — shared with codetrace --important-file
```

## What to commit vs ignore

| Commit | Usually gitignore |
|---|---|
| Brief, gaps, important, compact JSON, Markdown/PDF, figures | Huge raw `node_data` trees, videos, `.coverage`, secrets |
| Small run inventory notes | Full duplicated run directories if already under `outputs/` |
| `codetrace/` itself (it's small, portable, and the point is to keep it in the repo) | `line_coverage/out/.coverage` (raw coverage.py data file, not the JSON report) and `run.log` if it's large |

Point at `outputs/run_…` (or equivalent) instead of copying unless the team needs a frozen snapshot. Keep trace JSON available for `--rebuild`; rendering a page should not require repeating training or simulation. The rendered pages are self-contained (payload inlined). Version the delivered `call-tree.html` in the shared menu repository and record its local/deployed URLs in the run inventory and `MAPPING.md`; the target repo may ignore its generated HTML. Publish `mosaic.html` only if requested. See [PUBLISHING.md](../../PUBLISHING.md).

## Naming

- Prefer stable relative paths from repo root.
- Keep `recorded_live.json` for the full trial; `recorded_values.json` for supplemental probes.
