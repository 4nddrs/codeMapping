## Card: `<id>`

| | |
|---|---|
| **Path** | `path/to/file.py` |
| **Symbol** | `Class.method` or `function` |
| **Lines** | Lstart–Lend |
| **Layer** | bootstrap \| orchestrator \| domain \| verify \| teardown \| failure |
| **Workflow node** | _(if any)_ |
| **Duration** | _(ms from trial, if known)_ |
| **Recorded ref** | `recorded_live.json` → `nodes.<name>` |
| **Gap refs** | _(ids or none)_ |

### Why

One to three sentences: why this call exists on **this** command’s path.

### Code

```python
# Paste the full function (or faithful extract). Prefer AST-bounded full def.
```

### Inputs (recorded)

| Name | Value (summarized) | Notes |
|---|---|---|
| | | |

### Outputs (recorded)

| Name | Value (summarized) | Notes |
|---|---|---|
| | | |

### Edges

- **Next:** `<id>`, …
- **On failure:** `<id>` \| none

### See also

-
