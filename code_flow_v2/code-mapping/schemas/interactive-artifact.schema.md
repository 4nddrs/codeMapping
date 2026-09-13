# Schema — Interactive artifact data files

Produced by [`../codetrace/`](../codetrace/) ([phases/07-interactive-artifact.md](../phases/07-interactive-artifact.md)).
These are **generated** files — do not hand-author them; this page documents
their shape only so you can debug, extend, or read them without re-running
the tool. The canonical description of the two rendered pages themselves
(what they show, how to navigate) is
[`../codetrace/README.md`](../codetrace/README.md); this schema covers the
JSON underneath.

All files land under `--out` (default `docs/code_mapping/line_coverage/out/`).

## `run.json`

One flat object, written right after the traced run finishes.

| Key | Type | Description |
|---|---|---|
| `command` | string | The command run, joined from argv after `--` |
| `exit` | int | Process exit code (0 on success) |
| `secs` | float | Wall-clock seconds |

Read back by `--rebuild` so the pages can still show the original command /
outcome without re-running.

## `coverage.json`

Unmodified `coverage.py` JSON report (`Coverage.json_report()`). Keyed by
absolute or root-relative file path (branch coverage on):

```json
{
  "files": {
    "path/to/file.py": {
      "executed_lines": [1, 2, 5, 8],
      "missing_lines": [6, 7],
      "missing_branches": [[8, 9]],
      "summary": { "num_statements": 42, "percent_covered": 66.7 }
    }
  }
}
```

`missing_branches` entries are `[line, branch_target_line]` pairs; a branch
line whose target appears here but the line itself is in `executed_lines`
means only one side of that branch was taken — this is what renders as
"partial" (amber) in both pages.

## `callgraph.json`

Written by `CallTracer.dump()`. Two arrays, in first-occurrence order
(`seq` is a global monotonic counter across both):

```json
{
  "calls": [
    { "file": "pkg/mod.py", "name": "Class.method", "first": 10,
      "count": 3, "seq": 0 }
  ],
  "edges": [
    { "cfile": "pkg/cli.py", "cline": 12, "cname": "main", "cfirst": 5,
      "via": "", "tfile": "pkg/mod.py", "tname": "Class.method", "tfirst": 10,
      "count": 3, "seq": 1 }
  ]
}
```

| Field | Meaning |
|---|---|
| `file` / `first` | file + the function's `co_firstlineno` (first **decorator** line if any — see [reference/dynamic-capture-python.md](../reference/dynamic-capture-python.md) #1) — together they key one function |
| `name` | qualified name, e.g. `Outer.method` or `outer.<locals>.inner` |
| `count` | how many times this function was entered |
| `cfile`/`cline`/`cname`/`cfirst` | the calling **line**, and the enclosing function that line is in (empty `cfile` = caller was outside the watched roots, or import-time) |
| `via` | non-empty when the real call passed through a foreign frame first (`contextlib`, `import`, a library callback name, `thread`) — see dynamic-capture reference #3–4 |
| `seq` | first-occurrence order, shared across `calls` and `edges` — used to break ties when laying out columns |

## `payload_call_tree.json`

What `call_tree.html` actually renders (built by `_calltree.py` from the two
files above + AST-extracted source). One object:

| Key | Description |
|---|---|
| `command`, `outcome`, `title`, `brand` | header text |
| `geom` | `{LH, HDR, world_w, world_h, ncols}` — layout constants + the canvas's total extent |
| `totals` | `{functions, edges, calls, lines, executed, columns, important}` |
| `main` | node id of the entry point (column 0) |
| `nodes[]` | one per function reached from the entry: `{id, file, name, start, def, end, src, nlines, ex[], mi[], partial[], calls, seq, w, h, x, y, col, important, via, innovation}` — `ex`/`mi`/`partial` are line numbers (coverage overlay clipped to this function's range); `x`/`y`/`col` are the laid-out canvas position |
| `workflow[]` | optional jump list for the header Stage picker. Built from `# ---` headings in `important.txt`: `{label, name}` per section, pointing at the earliest card that matches a pattern in that section. Empty / omitted hides the picker. A published page may also hand-author this as `[label, name]` pairs. |
| `innovation` | optional; present when an innovation file was applied (`--innovation-file FILE`, or `codetrace_innovation.json` in `--root`): `{label, definition, review, functions, cards, unmatched[]}`. Each marked node carries `innovation: {role, summary, provenance, ranges[{start, end, what, text}]}`; see [innovation.schema.md](innovation.schema.md) |
| `important_label` | optional legend text for the ★ marks, copied from `important_label` in the applied innovation file (e.g. "★ curated stage (not innovation)"); pages with frames otherwise label ★ "★ curated critical path" |
| `edges[]` | `{from, line, to, n, seq, via, synthetic}` — `from`/`to` are node ids; `synthetic` marks a fallback edge added so every reached node has *some* path back to the entry |
| `modules` | optional; copied from `callgraph.json` `modules`. `{key: {t, extra, params, n_params, children, more_children, calls}}` for each PyTorch module that appeared in a sampled value (and its submodules, up to 800 modules): class name, `extra_repr()` (≤160 chars), own parameter/buffer shapes `{name: shape}`, parameter count, `children` `{attribute: key}` (≤32, `more_children` counts the rest), and `calls[]` `{in: [argument shapes], out: shape}` for the first two distinct observed forward signatures. A summarized module value carries `"module": key` |
| `nodes[].samples[]` | recorded calls of this card (first two): `{n, inst, args, locals, ret \| yielded, status, executed_lines, steps, stmt_first, stmt_left, stmt_hits, exit_after, steps_truncated}`. `steps[i] = {line, after, vars, coalesced}`: `vars` are the summarized locals that changed, taken as statement `line` starts (`line` null: the call's final changes, at exit), right after statement `after` ran (`coalesced`: also changes from skipped loop passes). `stmt_first[s]` / `stmt_left[s]` are the number of steps recorded when statement `s` (its first line) was first entered / first left, so a name's value as `s` first started is its last step (or entry argument) below `stmt_first[s]`, and right after `s` its last one below `stmt_left[s]`. `stmt_hits[s]` counts runs of `s`; `steps_truncated` is the step count where recording stopped (indexes above it were not recorded). Older captures have `steps[i] = {line, vars}` taken at calls and no `stmt_*` keys |

Back/sideways edges (`to.col <= from.col`) are **grouped by target at render
time**, in the viewer, not in this payload: a target with two or more of them is
drawn as one trunk plus a numbered circle, and the individual strands are in the
DOM but transparent until the circle is hovered or clicked. The payload is
unchanged by this — the grouping is presentation only, so `edges[]` still lists
every edge individually and a re-render with a different rule needs no re-trace.
See [`../codetrace/README.md`](../codetrace/README.md#bundled-callers-the-numbered-circle).

Functions not reachable from `main` through call-time edges (see
dynamic-capture reference #5) are **not** in `nodes[]` at all, even if they
appear in `callgraph.json` — they were called only at import time, or drawn
in only when `--keep-imports` is passed.

## `payload_mosaic.json`

What `mosaic.html` renders (built by `_mosaic.py`). One object:

| Key | Description |
|---|---|
| `command`, `outcome`, `title`, `brand` | header text |
| `totals` | `{files, files_loaded, lines, statements, executed}` |
| `files[]` | every `.py` under the watched roots, whether imported or not: `{path, src, nlines, ex[], mi[], partial[], loaded, nstmt}` |

`loaded: false` files (never imported this run) still carry full source but
render collapsed, in a labelled band, per
[`../codetrace/README.md`](../codetrace/README.md).

## Relationship to this pack's other schemas

- These files are **evidence of what ran**, same rank as any other dynamic
  coverage/call-tree source in
  [reference/sources-of-truth.md](../reference/sources-of-truth.md) — they
  do not override `recorded_live.json`'s per-node I/O values, and
  `recorded_live.json` does not override these for "did this line execute."
- `important.txt` ([schemas/important.schema.md](important.schema.md)) is
  consumed directly via `--important-file` — one file, not a fork. See
  [phases/07-interactive-artifact.md#reconciling-importanttxt](../phases/07-interactive-artifact.md#reconciling-importanttxt).
- Nothing here replaces `GAPS.md` — gaps this phase introduces (import-time
  drop, third-party walk-through, sampled values) still need entries there.
