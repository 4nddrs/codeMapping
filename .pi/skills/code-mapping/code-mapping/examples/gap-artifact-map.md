# Example — Artifact map (GaP Libero)

How the originating project’s files correspond to this skill pack’s generic names.

| Skill-pack artifact | GaP path (examples) |
|---|---|
| `BRIEF.md` | This example brief; intent also in PDF front matter |
| `important.txt` | `docs/code_mapping/line_coverage/important.txt` |
| `recorded_live.json` | `docs/code_mapping/recorded_live.json` |
| `recorded_values.json` | `docs/code_mapping/recorded_values.json` |
| Run inventory | `outputs/run_20260903_102839/` (+ PDF references) |
| Coverage / call tree | `docs/code_mapping/line_coverage/` (`coverage.json`, `callgraph.json`, codetrace) |
| Figures | `docs/code_mapping/figures/01_…08_…` |
| Mapping document | `docs/GaPCodeMapping.pdf` (also `docs/GaP_Libero_Quickstart_Code_Mapping.pdf`) |
| Compactors | `docs/code_mapping/parse_live_trace.py` |
| Supplemental capture | `docs/code_mapping/capture_values.py` |
| Diagram generator | `docs/code_mapping/diagrams.py` |
| PDF builder | `docs/code_mapping/build_pdf.py` |
| Gaps | Embedded in PDF + `important.txt` caveats; new mappings should use a standalone `GAPS.md` |
| Phase 7 tool | `docs/code_mapping/line_coverage/codetrace/` — identical copy of [`../codetrace/`](../codetrace/) |
| Phase 7 output | `docs/code_mapping/line_coverage/out/` (`call-tree.html`, `mosaic.html` + their JSON) once run; `capture.sh` there wraps the exact `codetrace.py` invocation used |

## Lesson for other projects

You do **not** need GaP’s scripts. You need:

1. A frozen brief
2. A SUCCESS run pointer
3. A curated important list with why
4. Compact live I/O JSON
5. Explicit gaps
6. A mapping document that walks the path
7. A viewable call tree in the shared menu, with verified URLs (unless opted out
   or unsupported; record the reason)

Project-specific parsers and PDF builders are optional scaffolding. Reuse the
saved trace for the normal phase-7 delivery rather than repeating the run.

One exception: unlike GaP's project-specific parsers and PDF builder, `codetrace/`
*is* meant to travel with the pack unmodified — it takes its scope (`--include`),
entry point, and importance list as arguments instead of assuming a layout, which
is what makes it safe to copy into an unrelated repo rather than reimplement.
