# Schema — Critical-path list (`important`)

File: `important.txt` (text). One symbol pattern per logical entry, with why-comments.

## Line grammar

```text
# --- section heading (optional; becomes a Stage jump in the call tree)
relative/path/to/file.py:qualified.name
#     why: free text (may wrap across following # lines)
#     votes: N   (optional)
#     layer: bootstrap|orchestrator|domain|verify|teardown|failure  (optional)
```

## Patterns

| Pattern | Meaning |
|---|---|
| `file.py:func` | Top-level function |
| `file.py:Class.method` | Method |
| `file.py:Class.*` | All methods of class (use sparingly) |
| `file.py:*` | All traced symbols in file (rare) |
| globs in path | e.g. `examples/*/scripts/*:run` |

## Rules

- Paths relative to repo root.
- Prefer concrete symbols over globs.
- Every kept entry **must** have a `why`.
- Comments alone are not entries.
- Blank lines allowed.

## Relationship to `codetrace --important-file`

This is the same file [phase 7](../phases/07-interactive-artifact.md) passes
as `--important-file` — one list, not a fork. The tool's actual (and only)
requirement, from [`../codetrace/_calltree.py`](../codetrace/_calltree.py):
a line is skipped if blank or `#`-prefixed; anything else is an
[`fnmatch`](https://docs.python.org/3/library/fnmatch.html) pattern matched
against the qualified name, its last segment, or (if it contains `:`) the
file-glob half against the path and the name-glob half against the name —
which is a superset of this schema's grammar (bare `name` and `Class.method`
patterns with no file prefix also work). This pack's `why:` / `votes:` /
`layer:` convention on the following `#` lines is exactly the kind of line
the tool already ignores, so no reformatting is needed either direction —
author once, use for both the mapping doc and the ★ marks in the rendered
pages. `# --- heading` comments additionally become the Stage jump list in
the call-tree header (first matching card per section). See
["Core-contribution functions"](../codetrace/README.md#core-contribution-functions)
in the tool's README for the rendered result.
