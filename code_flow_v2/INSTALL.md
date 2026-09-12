# Installing this skill pack

## Option A — Keep in the repo (recommended for team share)

Leave `skillsCodeMapping/` at the repository root. Point agents at:

```text
skillsCodeMapping/code-mapping/SKILL.md
```

Optionally copy `rules/code-mapping.mdc.example` to:

```text
.cursor/rules/code-mapping.mdc
```

(adjust frontmatter if your Cursor version expects different fields).

## Option B — Personal Cursor skill (all projects)

```bash
mkdir -p ~/.cursor/skills/code-mapping
cp -R skillsCodeMapping/code-mapping/* ~/.cursor/skills/code-mapping/
# Also copy OBJECTIVE next to it or merge the objective into SKILL.md
cp skillsCodeMapping/OBJECTIVE.md ~/.cursor/skills/code-mapping/OBJECTIVE.md
```

Ensure paths inside `SKILL.md` still resolve (they use relative links under `code-mapping/`).

## Option C — Per-project brief only

Install the skill personally (B), and in each repo only maintain:

- `docs/code_mapping/BRIEF.md`
- artifacts produced by the phases

## Starting a new mapping (agent prompt)

```text
Follow skillsCodeMapping/code-mapping/SKILL.md.
Create docs/code_mapping/ from the templates.
Command under study: <PASTE COMMAND>
Complete phases 1–6, then render the call-tree navigator from the saved trace,
add it to the shared sessions menu, and return verified delivery URLs.
```

The navigator is included by default after the evidence and documentation.
To limit delivery, say `data and documentation only`, `local only`, or
`do not publish`. For an existing mapping, point the agent at its saved trace
to rebuild the page without rerunning the target.

Finished pages are collected in the shared sessions menu
(`/mnt/sata1/andres/menuCodeMapping` on linux3, git repo
`https://github.com/4nddrs/codeMapping.git`) — see `PUBLISHING.md` for how a
page gets there, the default local URL (`http://localhost:8766/`), and the
authorized direct-to-`main` push and deployment verification workflow.

`codetrace/` (phase 7's tracer) needs Python and one pip package
(`coverage`), installed into the target project's own environment —
not a `uv run --with` overlay or equivalent. See
`code-mapping/reference/dynamic-capture-python.md` #6 if unsure why.

## Language

All pack content is English. Produce mapping artifacts in English unless the user requests otherwise.
