# Schema — Paper-innovation lines (`innovation.json`)

Optional. It marks the exact source lines that implement the contribution the
brief studies, such as a paper's method or a mechanism the repository adds. The
call-tree page then gives those cards a **green frame**.

On a page that has frames, the ★ legend reads "★ curated critical path" unless
`important_label` sets different text. ★ keeps marking the curated reading path
from `important.txt`, and green marks what is new. A function can have both.

File: `docs/code_mapping/innovation.json`. Pass it as `codetrace --innovation-file`
(relative paths resolve from the current directory), or save it as
`codetrace_innovation.json` in `--root` to have it read automatically. Start from
[../templates/innovation.template.json](../templates/innovation.template.json).

## Shape

```json
{
  "label": "Patch Policy innovation",
  "definition": "Legend tooltip: what the green frames mean for this project.",
  "important_label": "★ curated stage (not innovation)",
  "review": {"date": "YYYY-MM-DD", "method": "how ranges were chosen", "excluded": ["file:function: why not"]},
  "functions": [
    {
      "file": "models/diffusion_policy/diffusion_policy.py",
      "function": "TransformerForDiffusion.__init__",
      "role": "core",
      "summary": "Card tooltip: what this function contributes.",
      "provenance": "The upstream code it differs from, and how.",
      "ranges": [
        {"start": 248, "end": 277, "what": "Line tooltip.", "text": "S_patches = n_obs_steps * self.n_patches"}
      ]
    }
  ]
}
```

| Key | Required | Meaning |
|---|---|---|
| `functions[].file` | yes | Path relative to `--root`, as shown on the card. |
| `functions[].function` | yes | Qualified name exactly as the card shows it (`Class.method`, `outer.<locals>.inner`). List each function once; when several cards share the name (a property getter and setter, or one card per call site), each card is framed with the ranges that lie inside it. |
| `functions[].role` | yes | `core`: lines that exist because of the contribution (solid frame). `supporting`: unchanged or inherited code where the new data or mechanism takes effect, or that makes it affordable (dashed frame). The role applies to every range in the entry. |
| `functions[].ranges[]` | yes, at least one | `start` and `end`: 1-based file line numbers inside the function, with `start <= end`. `what` (required): the line tooltip. `text` (optional but recommended): the stripped source of line `start`, checked when the page is built. |
| `summary`, `provenance` | recommended | `summary` is the card tooltip. `provenance` is the upstream comparison that justifies the role. |
| `label`, `definition`, `important_label`, `review` | optional | Legend text and tooltip, a replacement label for the ★ legend, and a record of how the ranges were chosen. |

## Rules

- Mark tight ranges that start and end on statements. Mark a whole function
  only when the whole function is the mechanism.
- Every range needs a `what`. Every function needs a `provenance` checked
  against the upstream code the project builds on: read both, don't rely on
  memory.
- Leave generic machinery unmarked even when it is on the critical path, for
  example schedulers, losses, EMA, normalizers, data loading, simulators,
  logging, and checkpoints.
- List rejected candidates and the reasons in `review.excluded`.

## What the build checks

Before the traced command runs, codetrace checks every entry. Each of these
stops the build with a one-line error:

- a missing file or bad JSON
- an entry without `file` or `function` as non-empty strings, or a function listed twice
- a missing or unknown `role`
- an empty `ranges` list
- a range without integer `start <= end`, or without `what`

After the run, the checks against source apply only to functions that the run
rendered. A range that lies outside every card of its function, or a `text`
that no longer matches the source, stops the page build with exit code 2. Fix
the file and use `--rebuild`. A listed function that the run never reached is
printed and recorded in `payload.innovation.unmatched`; it is not an error.

## Choosing the ranges and rendering them

- Method: [phase 3 — Paper innovation](../phases/03-critical-path.md#paper-innovation-optional)
- Rendered result: ["Paper-innovation frames"](../codetrace/README.md#paper-innovation-frames-green)
