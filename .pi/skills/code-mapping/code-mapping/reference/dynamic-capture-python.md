# Dynamic capture, Python: how it actually works

Background for [phases/07-interactive-artifact.md](../phases/07-interactive-artifact.md)
and for anyone extending [`../codetrace/`](../codetrace/) or hand-rolling a
capture for a case it doesn't fit. Use `codetrace` first — this page exists
so the reasons behind its design choices aren't lost, and so a hand-rolled
capture (for a non-Python target, or a runtime `codetrace` genuinely can't
attach to) doesn't re-discover the same pitfalls the slow way.

## The two signals, combined

- **`coverage.py`** (`branch=True`) answers *which lines ran*, including
  which side of a branch. Cheap, mature, gives you `executed_lines`,
  `missing_lines`, `missing_branches` per file.
- **`sys.setprofile`** answers *what called what*. A `call` event fires with
  the callee's frame; `frame.f_back` is the caller. Recording
  `(caller file, caller line, callee)` for every call event, across the
  whole run, is a real call graph — not a guess from static imports, so it
  is correct through dynamic dispatch, decorators, and callbacks that a
  static analyzer would miss or over-approximate.

Run both over the **same** invocation of the real command. Two runs of
"the same" command are not guaranteed to take the same branches (perception
tournaments, cache hits, thread scheduling) — coverage and the call graph
must come from one process, one execution.

## Eight things that will bite you if you build this from scratch

1. **A decorated function's `co_firstlineno` is the first decorator's line,
   not the `def` line.** `frame.f_code.co_firstlineno` for
   ```python
   @a
   @b
   def f(): ...
   ```
   is the line of `@a`, not `def f`. If you locate functions by AST and match
   on `def`'s line number, decorated functions won't resolve. Match against
   *either* the AST node's own `lineno` (its `def`) or
   `min(node.lineno, *(d.lineno for d in node.decorator_list))` — try both.

2. **Nested functions carry their parent in the qualname.** A closure defined
   inside `outer` reports `co_qualname` as `outer.<locals>.inner`. Comprehensions
   and lambdas report a name starting with `<` (`<listcomp>`, `<lambda>`) —
   treat these as not-a-card and attribute the call to the nearest enclosing
   *named* frame by walking `f_back` until the name doesn't start with `<`.

3. **The caller you actually want is often several frames up.** `f_back` is
   frequently a `contextlib` generator wrapper (any `with` block), a
   dataclass-generated `__init__`, a library's callback trampoline, or a
   thread bootstrap — none of it your code. Walk `f_back` past any frame
   whose file isn't under the repo roots you're watching, and label the edge
   with what you walked through (`via: contextlib`, `via: import`, …) rather
   than silently attaching to the wrong caller or giving up.

4. **Thread bodies lose their caller entirely** unless you catch it before the
   thread starts. By the time a thread's target function fires a `call`
   event, `f_back` is the thread bootstrap, not the line that called
   `.start()`. Wrap `threading.Thread.start` (or monkeypatch it once, at hook
   install time) to snapshot the caller of `.start()` per-thread, and use
   that as the fallback caller for the first frame observed on that thread.

5. **Import-time noise dominates a naive graph.** Every module-level
   statement runs inside a synthetic `<module>` frame the first time it's
   imported. If you don't special-case this, decorators, registration
   patterns (`@app.route`, tool/skill registries, dataclass field defaults
   evaluated at class-body time) all show up as edges from `<module>`, and
   anything only reachable through them looks like a root with no caller.
   Two fixes, applied together: (a) drop edges whose caller frame is a
   `<module>` body — that work happened because something got imported, not
   because your entry point called it; (b) after building the graph, keep
   only nodes **reachable from the real entry point** via the remaining
   call-time edges, and drop everything else. Without step (b) you'll still
   have orphaned import-time helpers sitting in the tree with no real caller.

6. **Never trace inside an ad hoc environment overlay.** Anything that
   constructs a temporary virtualenv or dependency overlay on top of the
   project's real one (`uv run --with <pkg>` and equivalents in other tools)
   can shadow packages that are already correctly installed in the real
   environment — including native/compiled ones that do runtime path
   discovery (CUDA toolkits, GPU libraries, anything that globs its own
   install location). This is not a coverage-specific problem; it will bite
   any tracing approach run the same way. Install the tracer's one
   dependency **into the project's own environment** and run through its
   normal invocation (`uv run --no-sync`, plain `python`, whatever the
   project already uses) instead. This one cost a full debugging session in
   the originating project — a GPU motion planner failed with an unrelated
   `TypeError` from `os.path.isdir(None)` three layers down in a
   third-party CUDA kernel cache, and the actual cause was the overlay
   shadowing `nvidia-*` packages, nothing to do with the traced code at all.

7. **`co_qualname` does not exist before Python 3.11.** On 3.10 and older a
   `call` event can only give you `co_name`, so every method arrives as
   `__init__` / `step` / `forward`, matches nothing in the AST, and is dropped.
   The whole tree collapses to module-level functions and the auto-detected
   entry point lands on whatever happens to reach the most of them. Resolve the
   qualified name from `(file, co_firstlineno)` when the bare name does not
   resolve — line numbers still identify a function uniquely. `codetrace` does
   this; a hand-rolled hook must too.

8. **The tracer only sees its own process.** This is obvious stated plainly and
   very easy to miss in practice, because the trace still looks healthy:

   - Wrapping a **launcher** (`torchrun`, `accelerate`, `mpirun`) traces the
     launcher. The ranks are children. Invert it — the launcher runs a per-rank
     wrapper, the wrapper runs the target under the tracer, and you trace one
     rank so the profiler does not skew collectives.
   - A **DataLoader with `num_workers > 0`** runs the entire per-sample pipeline
     (`__getitem__`, file reads, decode, normalization, collation) in worker
     subprocesses. None of it appears. Set workers to 0 for the capture and
     declare it; then record the multi-worker path as unmapped.
   - The same holds for `subprocess`, multiprocessing pools and RPC.

   Diagnosing this is easy once you suspect it: list the `(file, name)` pairs in
   `callgraph.json` and check whether the functions you *know* must have run are
   there. Keeping both traces — one with workers, one without — turns the gap
   into evidence rather than a claim.

## A viewer note that is easy to get wrong

Not a capture pitfall, but it bit the rendered page and is worth stating once: in the
viewer, a `pointerdown` handler that guards with `if (e.button !== 0) return;` **must** have
a matching guard on `pointerup`, or a non-primary release runs the primary-button action
chain. And the button alone is not enough — macOS Ctrl+click and touch long-press raise
`contextmenu` with `button === 0`, so pair the button check with a flag set by the
`contextmenu` handler and cleared on the next `pointerdown`.

## Why this is one process, not `python -m cProfile` + `coverage run` as two

Running two separate tools over two separate invocations means two separate
executions of a possibly-nondeterministic program (perception tournaments,
thread scheduling, cache state). `codetrace` runs `coverage.start()` and
installs the profile hook in the same process, around one `runpy` invocation
of the target, so the call graph and the line coverage are guaranteed to be
from the same execution.

## If you must hand-roll this for a non-Python target

There's no bundled tool for it here. The shape of the problem transfers:

- Something that reports "line N of file F executed" (most languages have a
  coverage tool with a JSON or LCOV-ish export).
- Something that reports real call edges — a language-level equivalent of
  `sys.setprofile`, a debugger's function-entry hook, or (weaker, static-only,
  clearly labeled as such) a call graph from the language's own build
  tooling if no dynamic option exists.
- The same reachability-from-entry pruning (item 5 above) applies regardless
  of language — a raw call graph is always noisier than what the entry point
  actually reached.

Document this explicitly as a gap in `GAPS.md` rather than silently
producing a thinner artifact — see
[phases/07-interactive-artifact.md#language-limits](../phases/07-interactive-artifact.md#language-limits).
