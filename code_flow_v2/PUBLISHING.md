# Publishing a finished call tree to the Code Mapping Sessions menu

Normal mappings finish with one page, `call-tree.html` (phase 7), after the
evidence and documentation. Rebuild an existing matching trace before
considering another training or simulation run. Explicit data-only, local-only,
and no-publish requests take precedence. Finished pages are collected in one
shared menu so anyone can open every session from one place:

```
/mnt/sata1/andres/menuCodeMapping/          (on linux3)
  index.html          the menu — one card per session
  README.md           the same list as a table, plus "Adding a session"
  projects/
    <slug>/index.html         one folder per project, the full call-tree page
    rldx1/train.html          a project with two traces gets two pages
    rldx1/inference.html
```

The menu is a folder **and** a git repo (`https://github.com/4nddrs/codeMapping.git`,
branch `main`). Its configured public site is
**https://roaring-kringle-be46b2.netlify.app/**. Keep these states distinct:

- **Local:** HTML is under `projects/`, the menu card points to it by relative
  path, and the card opens the expected page at **http://localhost:8766/**.
- **Pushed:** the intended menu/page changes reached `origin/main`.
- **Deployed:** the public menu and direct project page have been verified to
  contain the new or updated mapping. A successful push alone is not proof.

Reuse the server already on port 8766 if it serves this checkout. If no server
is running, start one from the menu directory (keep it running in a persistent
session):

```bash
cd /mnt/sata1/andres/menuCodeMapping
python3 -m http.server 8766 --bind 127.0.0.1
# menu: http://localhost:8766/
# page: http://localhost:8766/projects/<slug>/index.html
# deployed page: https://roaring-kringle-be46b2.netlify.app/projects/<slug>/index.html
```

If another service owns 8766, do not terminate it blindly; identify the correct
menu server and report its actual working URL. The page also opens from disk at
`/mnt/sata1/andres/menuCodeMapping/projects/<slug>/index.html`.

Pages must stay **self-contained** — source, coverage, values and fonts all
inside the one HTML file, no network fetch — because they are opened from disk.
`codetrace/` already produces exactly that.

## Adding a session — the short version

```bash
# 1. render the existing trace (phase 7):
python code_flow_v2/code-mapping/codetrace/codetrace.py --rebuild \
    --out docs/code_mapping/line_coverage/out \
    --important-file docs/code_mapping/important.txt
# → <out>/call-tree.html + payload_call_tree.json; preserves the recorded run
# 2. let the helper fill the card from the trace's own numbers and copy the page:
python code_flow_v2/code-mapping/codetrace/menu_card.py \
    --out docs/code_mapping/line_coverage/out \
    --slug perturb_flow --name "perturb_flow" --tag "training · libero_spatial" \
    --what "Two optimizer steps of the joint action+future-image flow policy, from dataset load to checkpoint." \
    --fam gap --copy
# 3. paste the printed <a class="run"> block into index.html (inside the
#    "Execution call trees" shelf), replace the totals strip with the printed
#    numbers, bump the shelf's <span class="n">, add the printed row to README.md
# 4. open http://localhost:8766/ and click the new card; verify the page and UI
# 5. complete the authorized origin/main commit/push, then verify deployment below
```

`--copy` places the page at `projects/<slug>/index.html` (use `--page train.html`
etc. for a second trace of the same codebase) and replaces the placeholder
`<title>Code trace</title>` with `--title` (default: the card name — for a pair
whose cards are just "Training" / "Evaluation", pass `--title "proj · Training"`
so the browser tab still says which project). Without `--copy` it only prints;
nothing in the menu is touched. `--force` overwrites an existing page.

Worked example — the perturb_flow pair (two traces of one codebase, grouped in a
`<div class="pair" style="--fam: var(--fam-cap)">` like RLDX-1):

```bash
python codetrace/menu_card.py --out out/train --slug perturb_flow --page train.html \
    --name Training --title "perturb_flow · Training" --tag "train_flow.py · libero_spatial" \
    --what "Two epochs × two optimizer steps of the joint flow policy …" --fam cap --copy
python codetrace/menu_card.py --out out/eval --slug perturb_flow --page eval.html \
    --name Evaluation --title "perturb_flow · Evaluation" --tag "eval_sr.py · one episode" \
    --what "One full 220-step episode …" --result "0/1 · 4-step ckpt" --fam cap --copy
```

## What a card contains, and where each number comes from

The card is the `<a class="run">` block (template:
[`code-mapping/templates/menu-card.template.html`](code-mapping/templates/menu-card.template.html)).
Every value is read off the trace, never typed from memory:

| Card field | Source |
|---|---|
| `href` and the `.local` path | `projects/<slug>/<page>` — relative, never absolute |
| name / slug tag / description | you: project name, what the run is, 1–2 sentences |
| `.cmd` | `payload_call_tree.json` → `command` (also `run.json`) |
| `.verdict` (e.g. `exit 0 · 51.0s`) | `payload_call_tree.json` → `outcome`; add a result if the run has one (`9/12 picked`, `reward 1.00`) |
| entry `main · file.py` | the payload node whose `id == main` |
| file size | `stat call-tree.html` |
| Line coverage `36.4% · 3,374/9,261` | `totals.executed` / `totals.lines` |
| Functions / Edges / Calls | `totals.functions`, `totals.edges`, `totals.calls` |
| `--fam` stripe colour | `gap` teal · `cap` violet · `rldx` amber · `data` blue (defined in `index.html` `:root`) |

The totals strip at the top of the menu is the sum over all cards: sessions,
functions traced, calls recorded, lines executed, lines in scope. The helper
prints the new sums; replace the five `<div class="tot">` values by hand.

## Rules

- One card per traced command. Two traces of one codebase go in one folder as
  two pages, grouped in a `<div class="pair">` (see the RLDX-1 block).
- Do not edit a page after copying it, except the `<title>`. If the trace
  presentation changes, rebuild from the saved trace and re-copy. If a new run
  changes the evidence, re-copy its page and update the card's numbers.
- Never put an absolute path or a machine name in a card; the folder must work
  when copied elsewhere.
- Keep the whole thing English, like the rest of the pack.

## Push to GitHub after the local card works

After the local checks, complete the configured menu commit/push when the
request or existing session instructions authorize publishing. Do not ask again
for permission already given. Honor explicit delivery opt-outs. A skill copied
to a different environment does not itself grant authorization to publish code
to this or another account.

The shared menu uses direct pushes to `main`; no PR is needed for an authorized
session update. Inspect the checkout and remote first, preserve unrelated work,
and update from `origin/main` with a fast-forward only. Stage only the intended
page/menu files (and skill-pack changes when requested):

```bash
cd /mnt/sata1/andres/menuCodeMapping
git status --short
git remote -v
git pull --ff-only origin main
git add index.html README.md projects/<slug>/
git diff --cached --stat
git commit -m "Add <slug> call tree to the sessions menu"
git push origin main
```

- Push only after the new local card opens the right page and totals look sane.
- Preserve history; never force-push. If pull/push fails, retain the local result
  and report the exact blocker instead of claiming publication.
- If the checkout is on another branch or has unrelated changes, reconcile the
  intended update safely before following the `main` commands above.

## Verify the deployed page and finish

After the push, check both the configured public menu and its direct project
path. Allow a bounded deployment wait, then verify the actual page rather than
accepting a fallback/index response as success:

1. Open `https://roaring-kringle-be46b2.netlify.app/`; confirm the new card and
   its relative target are present.
2. Open `https://roaring-kringle-be46b2.netlify.app/projects/<slug>/<page>`;
   check the expected title, trace identity and representative functions, and
   exercise the relevant navigator controls in a browser.
3. Record the URLs and delivered commit in the run inventory and `MAPPING.md`.
   Return the direct localhost:8766 URL and the verified public project URL.

If the site has not deployed or configuration/authentication is unavailable,
report local success and pushed status separately from the deployment blocker.
Keep the local link usable; do not invent a public URL or say the site is live
without verification. Use an existing authorized deployment mechanism if the
site needs a manual publish; do not create another site to work around missing
configuration.

## Versioning this skill pack

The working pack is `/mnt/sata1/andres/code/code_flow/code_flow_v2/`; its
versioned copy is `code_flow_v2/` in the shared menu repository. When the user
requests pack changes and a push, sync the intended source changes into that
copy, review the diff, and include `code_flow_v2/` in the same authorized commit
or a separate scoped commit. Exclude caches, environments, and generated run
artifacts. Do not initialize a nested Git repository in the working pack.
