---
name: code-mapping
description: >-
  Forensic code mapping from a live run: scope one command, capture traces and
  coverage, curate the critical path, record real I/O values, document honest
  gaps, and produce durable documentation plus a viewable call-tree navigator.
  Use when the user asks for code mapping, run forensics, critical-path
  documentation, live I/O capture,
  mapping a SUCCESS/FAILURE trial, replicating docs/code_mapping-style work,
  or asking for an interactive/zoomable call-tree navigator like a prior
  mapping's published page. Do not use for generic architecture docs without
  a real run. The navigator is part of the normal mapping workflow.
---

# Code Mapping (from a live run)

Follow [OBJECTIVE.md](../OBJECTIVE.md). Deliver **data + documentation + a viewable call tree**, in that order. Honor explicit data-only, local-only, or no-publish requests.

## Hard rules

1. **Evidence over narrative.** Numbers and call order come from a real trial. Never invent I/O.
2. **Phases in order.** Do not write the final mapping document before phases 1–5 are closed (or explicitly waived with reason).
3. **One command per trace.** Do not expand a trace's scope without updating its
   brief. When the user requests all important commands in a repository, use
   the [command survey](reference/command-survey.md) to plan multiple traces.
4. **Curate.** A raw call graph is input; the critical-path list is the product.
5. **Honest gaps.** Cache hits, RPC, skipped perception, missing symbols — document them.
6. **No secrets.** Strip API keys, tokens, and `.env` contents from all artifacts.
7. **English** for all mapping artifacts unless the user requests another language.

## Before you start

1. Read this file and [OBJECTIVE.md](../OBJECTIVE.md).
   Use [QUICKSTART.md](../QUICKSTART.md) for the complete sequence and
   [PUBLISHING.md](../PUBLISHING.md) for local/public delivery and browser checks.
2. Copy [templates/brief.template.md](templates/brief.template.md) into the project (e.g. `docs/code_mapping/BRIEF.md`) and fill it from the request and available evidence; resolve missing scope before capture.
3. Confirm where run outputs live (logs, traces, `outputs/`, coverage dirs).
4. Open [checklists/phase-gates.md](checklists/phase-gates.md); tick gates as you go.

## Phases (mandatory order)

| # | Phase | Guide | Primary outputs |
|---|---|---|---|
| 1 | Scope | [phases/01-scope.md](phases/01-scope.md) | `BRIEF.md` |
| 2 | Capture | [phases/02-capture.md](phases/02-capture.md) | run pointer, coverage/call-tree, raw traces |
| 3 | Critical path | [phases/03-critical-path.md](phases/03-critical-path.md) | `important.txt` (or equivalent); optional `innovation.json` |
| 4 | Live I/O | [phases/04-live-io.md](phases/04-live-io.md) | `recorded_live.json`, optional `recorded_values.json` |
| 5 | Honest gaps | [phases/05-honest-gaps.md](phases/05-honest-gaps.md) | `GAPS.md` |
| 6 | Documentation | [phases/06-documentation.md](phases/06-documentation.md) | mapping Markdown/PDF + figures |
| 7 | Interactive artifact + shared menu | [phases/07-interactive-artifact.md](phases/07-interactive-artifact.md) | published `call-tree.html` — the only page this phase returns |

Read the phase guide **before** doing that phase. Use schemas under `schemas/` when writing JSON/Markdown artifacts. Complete phase 7 after phases 1–6 for normal mapping requests; no separate request for a website is needed. Rebuild a matching saved trace instead of rerunning training or simulation. Record explicit user opt-outs, unsupported languages, or rendering/publishing blockers in the brief or `GAPS.md`; do not claim a missing page is complete.

## Suggested project layout

See [reference/artifact-layout.md](reference/artifact-layout.md). Default:

```
docs/code_mapping/
  BRIEF.md
  GAPS.md
  important.txt
  innovation.json           # optional: reviewed lines implementing the studied contribution
  recorded_live.json
  recorded_values.json      # optional supplemental capture
  function_catalog.md       # or per-section cards
  figures/
  MAPPING.md                # or build toward a PDF
  runs/                     # notes linking to absolute/relative run dirs
  line_coverage/            # phase 2/7: coverage, call graph, the codetrace/ tool, out/
```

## Schemas and templates

- Brief: [schemas/brief.schema.md](schemas/brief.schema.md) · [templates/brief.template.md](templates/brief.template.md)
- Important list: [schemas/important.schema.md](schemas/important.schema.md) · [templates/important.template.txt](templates/important.template.txt)
- Innovation lines (optional): [schemas/innovation.schema.md](schemas/innovation.schema.md) · [templates/innovation.template.json](templates/innovation.template.json)
- Recorded live: [schemas/recorded-live.schema.md](schemas/recorded-live.schema.md) · [templates/recorded-live.template.json](templates/recorded-live.template.json)
- Recorded values: [schemas/recorded-values.schema.md](schemas/recorded-values.schema.md) · [templates/recorded-values.template.json](templates/recorded-values.template.json)
- Function cards: [schemas/function-catalog.schema.md](schemas/function-catalog.schema.md) · [templates/function-card.template.md](templates/function-card.template.md)
- Gaps: [schemas/gaps.schema.md](schemas/gaps.schema.md) · [templates/gaps.template.md](templates/gaps.template.md)
- Doc outline: [templates/mapping-doc.outline.md](templates/mapping-doc.outline.md)
- Interactive artifact data (phase 7): [schemas/interactive-artifact.schema.md](schemas/interactive-artifact.schema.md)

## Reference (read when needed)

- [reference/sources-of-truth.md](reference/sources-of-truth.md) — what beats what
- [reference/io-summarization.md](reference/io-summarization.md) — how to compress arrays/tensors
- [reference/anti-patterns.md](reference/anti-patterns.md)
- [reference/diagram-types.md](reference/diagram-types.md)
- [reference/dynamic-capture-python.md](reference/dynamic-capture-python.md) — how the coverage + call-graph capture actually works, and its pitfalls
- [checklists/definition-of-done.md](checklists/definition-of-done.md)

## Interactive artifact tool

[`codetrace/`](codetrace/) — a portable, single-dependency tracer that renders
the navigator: a zoomable call tree with an arrow from every call site, line
coverage on every card, ★ marks from `important.txt`, bundled back-edges behind
a numbered circle (hover to fan out, click to pin, right-click for the call-site
list), and a shortcut panel that starts collapsed. It also renders a line-coverage mosaic,
which is published only if asked. Copy the folder into a target repo and run it
per [phases/07-interactive-artifact.md](phases/07-interactive-artifact.md); read
[`codetrace/README.md`](codetrace/README.md) for the full CLI and how the page
works. Render phase 7 by default after the evidence and documentation, add
`call-tree.html` to the shared sessions menu, and verify the localhost:8766
link. Follow [PUBLISHING.md](../PUBLISHING.md) to push and verify the configured
deployment within existing user authorization. Return actual verified URLs;
`mosaic.html` remains an optional secondary view.

## Worked example (this repo)

- [examples/gap-libero-quickstart-brief.md](examples/gap-libero-quickstart-brief.md)
- [examples/gap-artifact-map.md](examples/gap-artifact-map.md)
- [examples/patch-policy-delivery.md](examples/patch-policy-delivery.md) — saved-trace
  rendering adapter, served-browser checks, and the configured publishing flow.

## Closing

After phases 1–6, complete [phase 7](phases/07-interactive-artifact.md) and run
[checklists/definition-of-done.md](checklists/definition-of-done.md). Do not stop
at a saved trace or Markdown report when a normal mapping request still needs
a viewable flow. Return the direct local call-tree URL and verified deployed
URL, plus the mapping document. Clearly distinguish a local page, a successful
git push, and a verified deployment; report any unfinished step and its cause.
