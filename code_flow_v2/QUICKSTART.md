# Agent quickstart (one page)

1. Read `OBJECTIVE.md` (pack root) and `code-mapping/SKILL.md`.
   For requests covering all important repository commands, first follow the
   [command survey](code-mapping/reference/command-survey.md), then apply this
   sequence to each selected command.
2. Copy `code-mapping/templates/brief.template.md` → `docs/code_mapping/BRIEF.md`; fill from the request and available evidence; freeze or record open questions.
3. **Capture** a SUCCESS run (or point at an existing one). Inventory it. For Python, preserve the matching `callgraph.json`, `coverage.json`, and `run.json` for the navigator.
4. Curate `important.txt` with **why** on every symbol; SUCCESS order.
5. Build `recorded_live.json` from trial dumps (summarize arrays). Optional `recorded_values.json` for narrow probes — label substitutions.
6. Write `GAPS.md` (caches, RPC, unexercised code, static-only failure paths).
7. Write `MAPPING.md` (or PDF) from `code-mapping/templates/mapping-doc.outline.md` using function cards.
8. **Render the navigator by default** using `code-mapping/phases/07-interactive-artifact.md`. Prefer `codetrace.py --rebuild --out <saved-trace-dir> --important-file docs/code_mapping/important.txt` over another training or simulation run. For a saved capture with a different value schema, follow that phase's adapter guidance and retain its documented render command. If a new capture is necessary and the command spawns processes, read that phase's "When the command spawns processes" first.
9. Add or update `call-tree.html` and its card in the shared sessions menu (`menuCodeMapping/`): `code-mapping/codetrace/menu_card.py` derives numbers from the trace and copies the page. Follow `PUBLISHING.md`; verify the menu and direct page at **http://localhost:8766/** by opening the new card in a browser and running the [browser acceptance checks](PUBLISHING.md#browser-acceptance-checks) before pushing.
10. Complete the authorized menu commit/push to `origin/main`, then verify the configured deployed project URL. Record any unavailable deployment or failed step accurately; git push alone is not deployment verification.
11. Complete `code-mapping/checklists/definition-of-done.md` after both local and public browser checks. Return the direct local URL, verified deployed URL, and mapping document; retain the [delivery record](PUBLISHING.md#record-the-delivery) and update the brief/checklist/gaps to reflect actual completion.

Explicit data-only, local-only, or no-publish requests take precedence. Record unsupported languages or delivery blockers honestly. Do not invent numbers or skip evidence/curation to build a page. The mosaic remains optional, and no second website is built beside the call tree.
