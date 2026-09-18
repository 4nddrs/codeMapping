---
name: code-mapping
description: >-
  Forensic code mapping from a live training run. Start Pi in this menu
  repo; the user gives a target project path. Install and prove that
  project's env, then follow code_flow_v2/ exactly and publish the
  call-tree page into this checkout. Use when given a target path or when
  the user asks for code mapping, run forensics, live I/O, or a call-tree
  navigator. Do not use for generic architecture docs without a real run.
compatibility: >-
  Python 3. Conda when the README has no env. coverage in that env. All
  user questions go through ask_user_choice. This menu repo is write-once
  delivery only.
---

# Code Mapping (Pi adapter)

`code_flow_v2/` is the rule. This file is only how Pi starts a session in
this menu repo. Do not invent a second method.

Read, in order, from this skill directory (symlinks into `code_flow_v2/`):

1. [OBJECTIVE.md](OBJECTIVE.md)
2. [code-mapping/PACK.md](code-mapping/PACK.md) — `code_flow_v2/code-mapping/SKILL.md`
3. [QUICKSTART.md](QUICKSTART.md)
4. [PUBLISHING.md](PUBLISHING.md)
5. The phase file for the phase you are in under `code-mapping/phases/`

Then do that. Copy templates from `code-mapping/templates/`. Run
`code-mapping/codetrace/` as those guides say.

## This menu repo

This checkout stores **published call-tree pages** (`projects/`, `index.html`,
`README.md`) and **the skill pack** (`code_flow_v2/`, `.pi/`). Nothing else.

Do **not** create `artifacts/`, `call_trees/`, `envs/`, logs, yaml env dumps,
markdown “call trees”, or extra folders here. Mapping evidence goes in the
**target** (`docs/code_mapping/`). The only menu writes for a mapping are:

- `projects/<slug>/*.html` via `menu_card.py --copy`
- the matching card in `index.html` and row in `README.md`

Edit `code_flow_v2/` or `.pi/` only when the user asked to change the skill.

## Pi session (before phase 1)

Start Pi **here**. The user gives the target path. That is the go-ahead.
Do not use Gentle AI clarify / plan / SDD. Two roles only: `scout` once,
then this parent. No worker, reviewer, or oracle.

**Every question** uses the `ask_user_choice` tool (2–4 options: label,
description, value). Never ask in prose, never a numbered list in chat
instead of the tool. Wait for the selection. If the tool is missing, stop
and say so — do not guess.

1. Confirm the target path exists. Work there for env, capture, and
   `docs/code_mapping/`. This checkout is `--menu` only.
2. Scout once (README + train command). If scout is missing, read the
   README yourself.
3. **Environment until the project actually runs** (parent, in the target):
   - Follow the README/lockfile recipe first (conda, mamba, uv, pip, poetry).
   - If there is no recipe, `conda create -n <slug> python=3.10` (or the
     README’s Python), install `requirements.txt` / `pyproject.toml`.
   - Use `conda run -n <env> --cwd <target> …` — not `conda activate` in
     `bash -lc`, and never run train from this menu cwd.
   - Install `coverage` in that env (`python -m pip install coverage`, never
     `uv run --with coverage`).
   - **Prove it:** `which python`, import the training stack, run the train
     entry `--help` or an equivalent smoke. `command not found` means the
     env is wrong — fix it, do not write a fake log.
   - If it fails, try alternatives in order: skip optional extras
     (flash-attn, etc.), CPU torch if CUDA is missing, README Python
     version, `pip` vs conda build of the same pin, 1-process launch
     instead of `torchrun --nproc_per_node=8`. After each try, prove again.
   - If still blocked, `ask_user_choice` with concrete next tries (retry
     CUDA, CPU, skip extra, stop). Do not invent a workaround folder here.
4. Default mapping target is **training**, bounded to **1 process** and
   **one real optimizer step** (not a full 8-GPU recipe). Then phases 1–7
   from `code_flow_v2` with `--kind training` on the menu card.
