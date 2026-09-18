# Use this pack on another PC

Clone the shared menu repository to get the current instructions, tracing tools,
and published pages together. No separate skill installation is required: point
the agent at the complete `code_flow_v2/` folder so its relative references work.

## 1. Clone the repository

These shell examples use `~/codeMapping`; choose another directory if needed.

```bash
git clone https://github.com/4nddrs/codeMapping.git "$HOME/codeMapping"
```

The agent entrypoint is now:

```text
~/codeMapping/code_flow_v2/code-mapping/SKILL.md
```

On a PC that already has this checkout, inspect its status and update it without
discarding local changes:

```bash
git -C "$HOME/codeMapping" status --short
git -C "$HOME/codeMapping" pull --ff-only origin main
```

Cloning downloads files; it does not run a target command or upload a new flow.
The agent carries out the mapping and publication instructions when asked.

## 2. Prepare the target project and access

- Clone or locate the repository you want to map on this PC. The menu checkout
  is a separate repository containing the workflow and published pages.
- Set up the target project's supported Python environment and dependencies.
  Install `coverage` in that same environment, for example with
  `python -m pip install coverage` after activating it. Do not use
  `uv run --with coverage`; see the
  [capture guidance](code-mapping/reference/dynamic-capture-python.md).
- Obtain the datasets, model weights, checkpoints, and hardware required by the
  selected commands. Cloning the menu does not copy the other PC's environments,
  datasets, training checkpoints, or raw captures. Published pages already
  contain their displayed source and sampled values.
- For publication, configure Git authentication on this PC using an account
  with write access to `4nddrs/codeMapping`, plus a Git commit name and email.
  An agent needs working terminal and browser access to run the workflow and
  verify delivery. Credentials are local setup, not files to commit.

The bundled tracer handles Python commands. The target's operating system,
native dependencies, GPU needs, and subprocess behavior may require additional
setup; the agent must record any unsupported paths or unavailable prerequisites.

## 3. Give the agent the task

Replace `<TARGET_REPO_PATH>` below with the target project's actual location.
This prompt explicitly authorizes the publication step:

```text
Use ~/codeMapping/code_flow_v2 to map the important commands in
<TARGET_REPO_PATH>.

Read code-mapping/SKILL.md, OBJECTIVE.md, QUICKSTART.md, and PUBLISHING.md
inside that pack. Survey the repository's important command families, run
representative real commands with documented bounds, and save a separate
trace and navigator for each distinct flow. Record missing prerequisites
and untested paths honestly.

Use ~/codeMapping as the shared menu checkout. Group this repository's
flows in one collapsed-by-default expandable section. Complete the local
browser checks at localhost:8766. You are authorized to commit and push
the intended mapping pages and menu changes to origin/main. Verify the
new flows on https://roaring-kringle-be46b2.netlify.app/ and return the
verified local and public URLs with any remaining blockers.
```

For one specific flow, replace the command survey with the exact command you
want traced. For an existing mapping, give the saved trace path so the agent can
rebuild its page without rerunning the target. Add `local only`, `data and
documentation only`, or `do not publish` when that is the intended scope.

Publication is part of the agent's workflow after authorization; it is not an
unattended uploader. The existing Netlify site can deploy changes pushed to the
shared repository, and the agent must check the public result rather than
treating a successful push as proof of deployment.

## 4. Use this PC's paths

When the pack remains inside the cloned menu, `menu_card.py` can locate that
checkout. If you copy the pack elsewhere, explicitly pass the menu directory to
the helper, for example `--menu "$HOME/codeMapping"`. Paths mentioning
`/mnt/sata1/andres/` in historical examples refer to the original PC; substitute
the actual paths on this one.

The agent should reuse a server already serving this menu on port 8766. To start
one yourself, keep this command running in a terminal:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory "$HOME/codeMapping"
```

Open <http://localhost:8766/> on this PC. Each PC has its own localhost server;
the shared public site remains <https://roaring-kringle-be46b2.netlify.app/>.
See [PUBLISHING.md](PUBLISHING.md) for the complete menu, browser verification,
Git push, and deployment procedure.

## Optional project rule

If your editor uses project rules, adapt
[`rules/code-mapping.mdc.example`](rules/code-mapping.mdc.example) and set its
pack path to the complete folder above. Copying only `SKILL.md` loses the phase
guides, templates, and tools it references.

## Language

All pack content is English. Produce mapping artifacts in English unless the
user requests otherwise.
