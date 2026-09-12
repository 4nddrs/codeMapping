# codetrace

Run a Python command **once**, then look at what it actually did.

You get two standalone HTML pages, each an infinite zoomable canvas (scroll to pan,
⌘/Ctrl+scroll to zoom) that you can open straight from disk — no server, no build:

| page | what it shows |
|---|---|
| **call-tree.html** | Every function the run reached. The entry point sits alone on the left; each function it called is one column to the **right**, with an arrow from the exact calling line to the callee's card. Card = that function's full source, with executed lines highlighted. |
| **mosaic.html** | Every source file, complete and untruncated, laid out as blocks. Executed lines highlighted, never-imported files collapsed into a labelled band. |

Arrows and coverage both come from **one real run** — not static analysis — so what
you see is what happened, including dynamic dispatch, decorators and callbacks.

## Install

Copy the `codetrace/` folder into the root of your repo. One dependency:

```bash
pip install coverage        # or: uv pip install coverage
```

> If you use `uv`, install coverage **into the project environment** and run with
> `uv run --no-sync`. Do **not** use `uv run --with coverage` — that builds an overlay
> environment that can shadow native packages. It cost me a debugging session: it made
> CUDA header discovery return `None` and killed the run.

> **Python 3.10 and older.** `co_qualname` only exists on 3.11+, so on older
> interpreters the tracer can record only a bare `co_name` — every method arrives
> as `__init__` / `step` / `forward` and never matches the AST's qualified names.
> `_calltree.py` recovers the qualified name from `(file, co_firstlineno)` when the
> bare name does not resolve; without that fallback a 3.10 run silently loses most
> of its methods and the auto-detected entry point lands somewhere absurd.

## Use

Put your command after `--`, exactly as you would type it:

```bash
python codetrace/codetrace.py -- python -m yourpkg.cli train --epochs 3
python codetrace/codetrace.py -- ./scripts/run_thing.py --fast
python codetrace/codetrace.py -- yourconsolescript run something
```

Then open `codetrace_out/call-tree.html`.

If your command needs environment variables, source them first — codetrace runs the
target in-process, so it inherits your shell:

```bash
set -a; source .env; set +a
python codetrace/codetrace.py -- yourcmd ...
```

## Options

| flag | meaning |
|---|---|
| `--root DIR` | project root (default: current directory) |
| `--out DIR` | where to write the pages (default: `codetrace_out`) |
| `--include PATH` | a source dir/file that is *yours*, relative to root. Repeatable. Default: auto-detected top-level packages — check the `watching …` line it prints and override if it guessed wrong. |
| `--entry NAME` | function to treat as the root of the tree. Default: the traced function that reaches the most others, which is normally your `main`. |
| `--title` / `--brand` | page title and the small label above the command line |
| `--label TEXT` | text for the outcome badge (default: `exit 0 · 12.3s`) |
| `--keep-imports` | keep functions that only ran while importing modules (default: drop them) |
| `--max-gap PX` | how far a callee may drop to sit level with its call site (default 300; raise for straighter arrows and a taller canvas) |
| `--important PATTERN` / `--important-file FILE` | mark core-contribution functions (see below) |
| `--no-values` | don't capture argument/local/return values (smaller page, faster) |
| `--rebuild` | redraw from the trace already in `--out` instead of running the command |
| `--no-mosaic` | skip the second page |

## Moving around

- **Follow a call**: click a `→ name` chip, or the underlined function name in the code.
- **Return**: press <kbd>Enter</kbd>, click the `↩ return` chip on a `return` line, or the
  `↩ Return` strip at the foot of any card. It takes you back to the **exact line that called
  this function** — the one you followed a chip from, or its first caller if you arrived by
  search. It does not reset the view to the top.
- **Undo a jump**: <kbd>Backspace</kbd> / the ← Back button retraces your steps regardless of
  what kind of jump they were.

## Bundled callers (the numbered circle)

A hot helper collects back-edges from all over the codebase — a logger, a config
`__getattr__`, a norm layer. Drawn one arrow per call site, a dozen dashed
curves converge on one card and the page becomes unreadable exactly where the
interesting function is.

So **incoming back/sideways edges are bundled**. Any function receiving two or
more of them gets:

- **one trunk line** into its card, plus a **numbered circle** at the knot where
  the strands converge. Collapsed, that is all you see. The number is the count
  of bundled **call sites**.
- **hover the circle** → the individual dotted origin strands fan out to their
  real call sites, and the trunk dims.
- **click the circle** → keeps them fanned out (a small light dot inside the
  circle marks the pinned state). Click again to release.
- **right-click the circle** → the list of those call sites, grouped by calling
  function with its file, each row showing the line number, `×N` when that line
  called more than once, and `via …` when the call passed through third-party
  code. **Click a row to fly to that caller's card at that exact line**;
  <kbd>Backspace</kbd> brings you back.

Functions with a single back-edge caller are drawn as a plain dashed arrow, as
before, and forward edges are untouched.

Two rules keep the feature honest:

- The right-click list is built from **the bundle's own edges**, so its count
  always equals the number on the circle. A caller that reaches the same
  function by an ordinary forward arrow already has its own visible arrow and is
  deliberately not listed — including those made the list disagree with the
  circle, which is worse than the omission.
- Nothing is hidden from the rest of the page: every strand is in the DOM with
  its own `data-i` / `data-f` / `data-t`, so focus highlighting, the ★-only
  filter and the caller chips all still see them. Focusing a card fans its own
  bundle open.

Bundling is a **rendering** choice and understates the arriving edge count until
expanded — record it in `GAPS.md` the same as any other presentation decision.

## Shortcut panel

Bottom-left. Click the header (or press <kbd>?</kbd>) to collapse it to a small
pill; the choice is remembered per viewer in `localStorage`, with every access
guarded — private windows and blocked site data make that accessor throw, not
just return null. Expanded it is a vertical list grouped into *Moving around*,
*Following calls*, *Bundled callers* and *Inspecting*, capped at `46vh` with its
own scroll so it can never push past the canvas on a short window.

## Values: right-click a line

Right-click any line to see what the variables on it held — shape and dtype for arrays and
tensors, nested keys for dicts, fields for objects, the first values, and the return value on
`return` lines. Right-click the header for everything the function saw: arguments at entry,
locals at exit, what it returned. Use ‹ › to step through the sampled calls.

These are real values from **the run you traced** (the first two calls of each function), not
re-executed — and captured at function *exit*, so a variable shows its final value. Pass
`--no-values` to skip this and get a much smaller page.

The popup is a pinned inspector: it closes on an outside click or <kbd>Esc</kbd>, or
when a jump moves the view — **not** on scroll, so you can wheel through a long value
dump without dismissing it. Right-click is also handled as a gesture rather than a
button: macOS Ctrl+click and touch long-press raise `contextmenu` with `button === 0`,
so the release that follows is suppressed explicitly. Without that, the pointerup ran
the ordinary left-click chain and closed the popup the right-click had just opened.

The panel is **pinned**: it stays up while you scroll and zoom, and closes on a left click
anywhere outside it, on <kbd>Esc</kbd>, or when a navigation moves the view.

> A context menu is not always a right button — macOS **Ctrl+click** and a touch
> **long-press** both raise `contextmenu` with `button === 0`. The viewer's `pointerup`
> handler therefore checks a flag set by the `contextmenu` handler *as well as* the button,
> because filtering on the button alone lets those two gestures run the whole left-click
> chain on release: following chips, toggling ★, and closing the popup that had just opened.

## Core-contribution functions (★)

Put the functions that *are* the paper's contribution in a text file, one glob per line, and
they're drawn in violet with a ★, with an **★ N** button in the header (or <kbd>i</kbd>) that
dims everything else:

```
# codetrace_important.txt   (auto-read from --root; or pass --important-file)
WorkflowExecutor.*          # every method of a class
execute_script_node
gap/runtime/nodes.py:*      # everything in a file
examples/*/scripts/*:run    # file glob + name
```

You can also click the ★ on any card to mark or unmark it by hand; those choices are kept in
your browser. After editing the file, `--rebuild` redraws without re-running the command:

```bash
python codetrace/codetrace.py --rebuild --out codetrace_out --important-file mine.txt
```

## Reading the call tree

- **Teal background** = line executed. **Amber** = a branch on that line was only taken one way. **Pink gutter** = statement never ran.
- **`→ name` chip** on a line = that line called `name`; click it to fly there. `×N` is the call count.
- **`↩ N callers`** in a card header cycles back through the places that called it; **← Back** / Backspace retraces your steps.
- **Amber dashed arrows** go back or sideways — a callee first reached from a shallower level.
  Where two or more of them arrive at the same function they are **bundled** into one
  trunk with a numbered circle — see [Bundled callers](#bundled-callers-the-numbered-circle).
- **`via …`** on a chip means the call passed through code that isn't yours (a `with` block's `contextlib`, a dataclass-generated `__init__`, a library callback) before landing in your function. The arrow still points at the line that caused it.
- Press `/` to find a function, `m` to return to the entry point, `0` to fit everything,
  `?` to collapse or expand the shortcut panel.
- **Stage** (header, next to find) jumps to a curated section of the run. The
  list is the `# --- heading` comments in `important.txt` — same file as the ★
  marks, first matching card per section. Hidden when that file has no headings.

## One card per call site, not per function

A function entered from two different places can do two different things: it takes a
different branch, or the `self` it is bound to dispatches somewhere else entirely. So a
card is **one call site**, not one function — the same `def` can appear several times
across the canvas, each card showing only the calls *that* entry actually made.

The clearest case in RLDX-1 is `BasePolicy.get_action`, which runs twice:

```
main:63 ──▶ BasePolicy.get_action (card A, col 2)
              L104 ─▶ RLDXSimPolicyWrapper.check_observation
              L105 ─▶ RLDXSimPolicyWrapper._get_action
              L107 ─▶ RLDXSimPolicyWrapper.check_action
                        │
              _get_action:520 ──▶ BasePolicy.get_action (card B, col 4)
                                    L104 ─▶ RLDXPolicy.check_observation
                                    L105 ─▶ RLDXPolicy._get_action
                                    L107 ─▶ RLDXPolicy.check_action
```

Same three lines, different `self`, different callees. Collapsed into a single card those
six out-edges sit on three lines with no way to tell which belongs to which entry, and the
second entry reads as an arrow going *back* to a card you already came from — you follow it
and land where you started. Per-call-site cards make the chain a chain: every hop moves
right, and each card's chips are the calls that entry really made.

Instances are keyed by `(function, calling card, calling line)`. Two calls from the *same*
line of the *same* card share one card and its `×N` count goes up — a loop body does not
spawn a card per iteration.

**The cap.** `MAX_INSTANCES = 8` in `codetrace.py` bounds cards per function. Past it,
further call sites collapse into one **merged** card wired from the call graph rather than
from a specific caller. Hot utilities are what hit this: a `rank_zero_print` or a config
`__getattr__` called from thirty places gets eight cards plus a merged ninth. Raise the
constant if you need more; the page grows roughly linearly with it.

**Effect on back-edges.** Per-call-site cards *duplicate* amber back-edges rather than add
new ones. When a shared leaf gets a card per parent, one logical edge such as
`is_global_zero:30 → get_global_rank` is drawn once per instance pair. On the RLDX-1
inference trace that turned 31 back-edges into 49 — all 49 are copies of just 11 logical
edges, 9 of them the logging chain `rank_zero_print → is_global_zero → get_global_rank`.
A rising back-edge count after this change is expected; a rising count of *distinct*
`from → to` name pairs is not, and means a real cycle appeared.

## What ends up at the far left

The leftmost card is the entry point, and everything else is to the right of it.

- Running a **script** (`python solver.py`) or a **package** (`python -m app`): the entry
  card is that file's top-level code, named `__main__`. Its `if __name__ == "__main__":`
  calls are real arrows out to the right.
- Running a **console script** whose wrapper lives outside your repo: the entry is your
  own first function — usually `main`.
- Either way you can force it with `--entry`.

## What is and isn't drawn

- **Only your code.** Third-party and stdlib frames are walked past, never drawn.
- **Import-time work is dropped** by default: functions that only ran because a module
  was imported (decorators, registration hooks) are not part of what your command *did*.
  Pass `--keep-imports` to see them.
- **Comprehensions and lambdas** attach to the function containing them.
- **Threads** are followed: a thread body attaches to the line that called `.start()`.
- If the target crashes, the partial run is drawn anyway.

## Cost

The profiler hook adds roughly 10–15% wall time on a mixed workload; coverage adds its
own overhead. Fine for a single run of most commands; not something to leave on in
production.

## Files

```
codetrace/
  codetrace.py    CLI, the tracer, and orchestration
  _calltree.py    call graph + coverage -> laid-out tree
  _mosaic.py      coverage -> file mosaic
  _render.py      payload + template -> standalone HTML
  templates/      the two canvas viewers
```

Output goes to `--out` (default `codetrace_out/`): the two HTML pages, plus
`callgraph.json`, `coverage.json`, the payloads, and `run.log` if you want the raw data.
