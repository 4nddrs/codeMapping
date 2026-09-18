# Code Mapping Skill Pack

Portable method for **forensic code mapping from a real run**: pick one command, capture what actually executed, curate the critical path, record live I/O, document honest gaps, and produce durable documentation.

The normal deliverable is **data + documentation + a viewable call-tree navigator**. Complete the evidence and documentation first, then [Phase 7](code-mapping/phases/07-interactive-artifact.md) renders the interactive, zoomable page from the same trace, adds it to the shared sessions menu, and verifies the local URL on port **8766**. Push to the configured menu repository and verify its deployment when authorized; return the actual usable URLs. Explicit data-only, local-only, and no-publish requests take precedence.

Start with [QUICKSTART.md](QUICKSTART.md) for the complete sequence, then use
[PUBLISHING.md](PUBLISHING.md) for menu updates, browser checks, Git push,
Netlify verification, and the evidence to save. These are the standing
instructions for future mappings; the process must not depend on chat history.

On another PC, follow [the clone and setup instructions](INSTALL.md), then
point the agent at the complete `code_flow_v2/` folder. No separate skill
installation is required.

Phase 7 returns **one page: `call-tree.html`**. The coverage mosaic is rendered beside it and published only on request, and no additional hand-authored "explained" site is built — phase 6's `MAPPING.md` is the prose deliverable. One command, one canvas, one document.

## What this is for

Use when you need to answer, for any codebase:

> For this exact command / trial, what ran, in what order, with which real values, why each step exists, and where failure would go?

Originated from the Graph-as-Policy Libero quickstart mapping (`docs/code_mapping/`, `docs/GaPCodeMapping.pdf`), generalized so the same process works on other projects.

## Layout

```
code_flow_v2/
  README.md                 ← you are here
  OBJECTIVE.md              ← the invariant goal
  QUICKSTART.md             ← one-page agent flow
  INSTALL.md                ← how to install / invoke
  PUBLISHING.md             ← where finished pages go: the shared sessions menu
  code-mapping/
    SKILL.md                ← agent entrypoint (read this first)
    phases/                 ← detailed phase guides (1-6 evidence/docs, 7 navigator + menu)
    schemas/                ← what each artifact must contain
    templates/              ← copy into a target repo and fill (incl. the menu card)
    checklists/             ← definition of done + phase gates
    reference/              ← IO rules, anti-patterns, layout, dynamic-capture technique
    codetrace/              ← portable tracer: renders phase 7's interactive pages;
                              menu_card.py hands a finished page to the menu
    examples/               ← GaP Libero as a worked brief
  rules/
    code-mapping.mdc.example  ← optional Cursor project rule
```

## How to use in a new project

1. Keep this complete folder in the cloned menu checkout, or copy/symlink the complete folder into the target repo. Point the agent at its `code-mapping/SKILL.md`; see [INSTALL.md](INSTALL.md).
2. Fill `code-mapping/templates/brief.template.md` for the command under study.
3. Tell the agent: *Follow the Code Mapping skill; brief is at …*
4. Work phases in order. Do not skip to documentation before live I/O and gaps are frozen.
5. Land artifacts under a project path such as `docs/code_mapping/` (see `reference/artifact-layout.md`).
6. Render the navigator, preferably with `--rebuild` from the saved trace, and finish the shared-menu workflow in [PUBLISHING.md](PUBLISHING.md). Report unsupported languages or delivery blockers honestly.

## Agent invocation

Typical prompts:

- “Start a code mapping for `<command>`; use `~/codeMapping/code_flow_v2/code-mapping/SKILL.md`.”
- “Continue code mapping from phase 3; brief is `docs/code_mapping/BRIEF.md`.”
- “Close the mapping: run the definition-of-done checklist.”

## What is in scope vs out of scope

| In scope | Out of scope |
|---|---|
| One canonical command / scenario | Mapping an entire monorepo |
| SUCCESS trial (+ optional FAILURE) | Speculative architecture without a run |
| Critical-path functions with live I/O | Every transitive dependency |
| Failure / abort edges | Every transitive third-party dependency |
| Honest gaps (cache, RPC, skipped paths) | Invented numbers or “typical” values |
| Rendering and delivering [phase 7](code-mapping/phases/07-interactive-artifact.md)'s `call-tree.html` by default | Building before evidence exists, ignoring delivery opt-outs, or adding a second website beside it |

## Local and deployed menu

- Local menu: http://localhost:8766/
- Configured public menu: https://roaring-kringle-be46b2.netlify.app/
- Versioned pack: `code_flow_v2/` in `https://github.com/4nddrs/codeMapping.git`

See [PUBLISHING.md](PUBLISHING.md) for adding sessions, syncing changes from
this local pack, and verifying both delivery URLs after an authorized push.

## Language

All skill text and templates are **English**.
