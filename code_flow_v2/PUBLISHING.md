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

For exact commands against the existing Patch Policy capture, see the
[Patch Policy delivery example](code-mapping/examples/patch-policy-delivery.md).

The menu is a folder **and** a git repo (`https://github.com/4nddrs/codeMapping.git`,
branch `main`). Its configured public site is
**https://roaring-kringle-be46b2.netlify.app/**. Keep these states distinct:

- **Local:** HTML is under `projects/`, the menu card points to it by relative
  path, and the card opens the expected page at **http://localhost:8766/**.
- **Pushed:** the intended menu/page changes reached `origin/main`.
- **Deployed:** the public menu and direct project page have been verified to
  contain the new or updated mapping. A successful push alone is not proof.

## Using a different PC

Follow [INSTALL.md](INSTALL.md) to clone the menu and complete the new-machine
setup. The `/mnt/sata1/andres/` paths in this document describe the original
machine; use the actual clone path on another PC. The complete `code_flow_v2/`
folder is versioned inside the menu checkout, so an agent can read it there
without a separate skill installation.

When `menu_card.py` runs from that cloned pack, it detects the containing menu
checkout. When using a copied pack, explicitly pass `--menu /actual/menu/clone`.
An explicit `--menu` always overrides discovery. For compatibility, a standalone
copy on linux3 can still use its existing menu checkout. If no menu is found,
`--copy` reports the missing path; printing card markup alone still works.

Cloning retrieves the workflow and published pages. It does not run a target,
install that target's environment or datasets, transfer Git credentials, or
start publishing. Give the agent the target repository and authorization to
publish, and provide GitHub access that can push to `4nddrs/codeMapping`.
The agent then follows the capture, menu, verification, and push steps below.
The existing Netlify deployment is associated with the shared repository;
pushing from another PC uses that same connection. A fork or different remote
needs its own deployment setup and will not update this site automatically.

## Local preview

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
#    repository group, or "Execution call trees" for an ungrouped session),
#    replace the totals strip with the printed
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

For a saved capture with a documented rendering adapter, use that command in
step 1 instead of a stock `--rebuild`; see
[Phase 7](code-mapping/phases/07-interactive-artifact.md#steps).
The helper prints proposed markup; it does not edit `index.html` or `README.md`.
Match the README's existing table columns when inserting its row.

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
| Function cards / Edges / Calls | `totals.functions`, `totals.edges`, `totals.calls`; cards can repeat a function |
| `--fam` stripe colour | `gap` teal · `cap` violet · `rldx` amber · `data` blue (defined in `index.html` `:root`) |

The totals strip at the top of the menu is the sum over all cards: sessions,
functions traced, calls recorded, lines executed, lines in scope. The helper
prints the new sums; replace the five `<div class="tot">` values by hand.

The helper's totals assume a **new session**. When replacing an existing page,
replace its card and README row, keep the session/shelf counts unchanged, and
subtract the old metrics before adding the new ones. Do not paste its proposed
add-one totals for a replacement. `totals.functions` counts call-site cards;
label that count as function cards where repeated functions could be mistaken
for distinct symbols. Report distinct-function counts separately when available.

## Browser acceptance checks

Run these checks on localhost before the push, then on the public site after
deployment. Use a browser or browser automation against the actual served URLs.

1. Open the menu; for a repository group, verify its summary expands and
   collapses with both a click and the keyboard, then expand it and click the
   session's card. Check the resulting URL, page
   title, entry point, recorded command, and outcome against the saved run.
2. Check stage navigation against the curated important list. Search for a
   representative function and navigate to its card. Repeated call sites may
   create multiple cards for one function; card counts are not symbol counts.
3. Open the value inspector with right-click or Ctrl-click. Navigate to the
   card first because off-screen cards are virtualized. Automated checks must
   exercise the real pointer/context-menu gesture, including pointer release.
4. Page through retained samples for representative functions and distinct
   captured contexts (for example validation, training, and rollout). Compare
   displayed primitives, shapes, numeric summaries, statistics scopes, and
   entry/exit labels with the evidence. Check missing/None values where present.
5. Check for JavaScript errors and compare the served embedded payload with
   the rendered payload, allowing documented title changes. A successful HTTP
   response or matching JSON alone does not establish working controls.
6. For functions with different branches across calling contexts, check the
   scope of the highlights against the actual call edges. Whole-run coverage
   can include mutually exclusive returns from separate invocations; never
   present it as a single invocation's path. A call observed only on another
   call-site card must be distinguished and navigable as another context, not
   added as an outgoing arrow on the current card. Exercise that context link,
   the genuine callee arrow, and Back. A single repeated call-site group can
   legitimately contain both branches when separate invocations took them.
7. Audit every displayed call expression across the command collection, not
   only the user's example. Reconcile observed project instance edges and
   dependency boundary records with rendered arrows. Classify unmatched static
   expressions as unobserved or outside the capture contract; a covered line
   does not prove every nested or short-circuited call executed. Check concrete
   module dispatch, native tensor methods, generated functions, multiline calls,
   comprehensions, exceptions, and helpers exceeding the instance cap.
8. For fresh traces, verify each card's highlights against its recorded
   `executed_lines` and each sampled invocation's lines against that group.
   Open representative dependency arrows with real clicks and inspect their
   inputs/outputs or explicit unavailable fields. Dependency source must remain
   a reference without fabricated internal coverage. Verify capture limits,
   recorder errors, unfinished samples and dropped records before publishing.
   If a capture lacks necessary evidence, preserve it and create a fresh run
   when authorized; rebuilding HTML cannot recover events that were never saved.
9. Check visibility as well as DOM existence. A long source line or several
   nested calls can push an arrow beyond a clipped card. Use a real browser
   pointer at the visible arrow's screen coordinates and keyboard activation;
   synthetic events on an off-screen element do not prove a usable control.
   Exercise the overflow control when a line has multiple destinations.

Save the check results as described below. If browser verification is unavailable,
record that limitation rather than claiming the UI was verified.

## Rules

- One card per traced command. Keep a repository's pages in one project folder.
  Group large collections in one closed-by-default
  `<details class="shelf repo-shelf" id="<slug>">`, with the repository title
  and flow count in `<summary class="shelfhead repo-summary">` and its cards
  in `.repo-content > .runs`.
  Reuse the menu's summary styling and keep its expand/collapse control visible.
  A two-page pair may retain `<div class="pair">` (see the RLDX-1 block).
  Preserve existing card URLs and the repository hash anchor; verify a hash
  link still reaches the visible repository summary. Publication scripts must
  preserve this grouping when replacing cards, counts, or generated sections.
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
- If Git rejects this known shared checkout because another local user owns it,
  inspect the path/remote and use
  `git -c safe.directory=/mnt/sata1/andres/menuCodeMapping -C /mnt/sata1/andres/menuCodeMapping <command>`
  for that checkout. Keep the exception scoped to each command.

## Verify the deployed page and finish

After the push, check both the configured public menu and its direct project
path. Allow a bounded deployment wait, then verify the actual page rather than
accepting a fallback/index response as success:

1. Open `https://roaring-kringle-be46b2.netlify.app/`; confirm the new card and
   its relative target are present.
2. Open `https://roaring-kringle-be46b2.netlify.app/projects/<slug>/<page>`;
   run the [browser acceptance checks](#browser-acceptance-checks). Netlify may
   redirect `index.html` to the directory URL; record the actual final URL.
3. Save the [delivery record](#record-the-delivery) and return the direct
   localhost:8766 URL and verified public project URL.

If the site has not deployed or configuration/authentication is unavailable,
report local success and pushed status separately from the deployment blocker.
Keep the local link usable; do not invent a public URL or say the site is live
without verification. Use an existing authorized deployment mechanism if the
site needs a manual publish; do not create another site to work around missing
configuration.

## Record the delivery

Keep a publication inventory such as `docs/code_mapping/runs/PUBLISHED.md`
and the browser results beside the existing run inventory. Include:

- The source trace and exact render command, including any adapter; generated
  page path and menu project path.
- The local and public menu/direct-page URLs, check time, expected title, and
  trace identity or canonical payload hash used for comparison.
- Which navigation, inspector, and sample checks passed, plus any limitations.
- Publication repository, branch, full pushed commit, and confirmation that
  `git ls-remote origin refs/heads/main` contains that commit (or a verified
  descendant). Record deployment verification separately from Git push.

Link this record from `MAPPING.md` and the SUCCESS run inventory. Update the
brief, gaps, and completion checklist so they no longer say rendering or
publication was not requested when it was completed. Keep sample limits,
subprocess exclusions, and the actual task outcome visible in both the report
and viewer; an exit-zero capture is not automatically task success.

## Versioning this skill pack

The working pack is `/mnt/sata1/andres/code/code_flow/code_flow_v2/`; its
versioned copy is `code_flow_v2/` in the shared menu repository. When the user
requests pack changes and a push, sync the intended source changes into that
copy, review the diff, and include `code_flow_v2/` in the same authorized commit
or a separate scoped commit. Exclude caches, environments, and generated run
artifacts. Do not initialize a nested Git repository in the working pack.

Compare the working pack and versioned copy before syncing; preserve unrelated
edits in either location. Copy the intended changed files with their relative
paths, then stage `code_flow_v2/` along with the requested site changes. Validate
the skill and its local links, review `git diff --cached --check` and the staged
diff, commit, and push using the sequence above. Confirm the intended files in
both pack locations match after the sync. Workflow-only edits do not require
rerunning a target capture or regenerating unchanged project pages.
