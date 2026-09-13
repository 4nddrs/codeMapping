#!/usr/bin/env python3
"""codetrace — run a Python command once, then draw what actually executed.

Produces two standalone HTML pages on a zoomable canvas:

  call-tree.html   every function the run reached, one column right of its
                   caller, arrows from the calling line to the callee's card
  mosaic.html      every source file, full text, executed lines highlighted

Usage
-----
    python codetrace/codetrace.py -- python -m yourpkg.cli --flag value
    python codetrace/codetrace.py -- ./scripts/train.py --fast
    python codetrace/codetrace.py -- yourconsolescript run thing

Everything after `--` is the command, exactly as you would type it.

See README.md for options.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import runpy
import shutil
import sys
import threading
import time
from itertools import count
from pathlib import Path

HERE = Path(__file__).resolve().parent
_boundary_spec = importlib.util.spec_from_file_location("_codetrace_boundaries", HERE / "_boundaries.py")
_boundary_module = importlib.util.module_from_spec(_boundary_spec)
_boundary_spec.loader.exec_module(_boundary_module)
BoundaryRecorder = _boundary_module.BoundaryRecorder

DENY_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", ".env", "node_modules",
    "third_party", "thirdparty", "vendor", "vendored", "build", "dist",
    "__pycache__", ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "site-packages", "htmlcov", ".idea", ".vscode", "codetrace",
    # common run-artifact dirs that happen to contain .py
    "outputs", "output", "runs", "wandb", "checkpoints", "logs", "artifacts",
}


# --------------------------------------------------------------------------
# source roots
# --------------------------------------------------------------------------
def autodetect_roots(root: Path) -> list[str]:
    """Top-level dirs/files holding this project's own Python."""
    out = []
    for p in sorted(root.iterdir()):
        if p.name.startswith(".") or p.name in DENY_DIRS:
            continue
        if p.is_dir():
            try:
                next(p.rglob("*.py"))
            except StopIteration:
                continue
            out.append(p.name)
        elif p.suffix == ".py":
            out.append(p.name)
    return out


# --------------------------------------------------------------------------
# value summaries (what a variable held, compactly)
# --------------------------------------------------------------------------
import dataclasses

MAX_SAMPLES = 2        # calls of each function whose values we keep (first N)
NODE_BUDGET = 900      # summary nodes per sample, so a giant dict can't blow up the page
MAX_STEPS = 40         # in-function snapshots per sample (see CallTracer._profile)
MAX_INSTANCES = 8      # separate cards per function, one per distinct call site.
                       # A function entered from two places can execute different
                       # branches and call different things (BasePolicy.get_action
                       # runs once as the sim wrapper and once as the policy), so a
                       # single merged card shows both invocations' out-edges at
                       # once and its back-edge loops onto itself. Past this many
                       # sites (hot helpers like a logger) they merge, as before.
MAX_LOCALS = 160       # names per snapshot. Must comfortably exceed a big function's
                       # local count: a long function assigns its most interesting
                       # result LAST (`out = ...` right before `return out`), so a low
                       # cap drops exactly the value a reader came to see. NODE_BUDGET
                       # still bounds the total work per snapshot.


def _num(x):
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return float(f"{x:.5g}")
    try:
        return float(f"{float(x):.5g}")
    except Exception:
        return str(x)[:24]


def _head(v, n=6):
    """First n flat values of an array-like, on CPU, as plain numbers."""
    if hasattr(v, "detach"):
        v = v.detach()
    if hasattr(v, "cpu"):
        v = v.cpu()
    flat = v.reshape(-1) if hasattr(v, "reshape") else v
    part = flat[:n]
    vals = part.tolist() if hasattr(part, "tolist") else list(part)
    return [_num(x) for x in vals]


def _safe_repr(v, limit=100):
    if type(v).__repr__ is object.__repr__:
        return None
    try:
        r = repr(v)
    except Exception:
        return None
    return r if len(r) <= limit else r[:limit] + "…"


def summarize(v, depth=0, budget=None):
    """JSON-able summary: shape/dtype for arrays, nested keys for dicts, head values."""
    if budget is None:
        budget = [NODE_BUDGET]
    if budget[0] <= 0:
        return {"t": "…"}
    budget[0] -= 1
    t = type(v)
    tn = t.__name__
    try:
        if v is None or isinstance(v, (bool, int, float, complex)):
            return {"t": tn, "r": repr(v)[:60]}
        if isinstance(v, str):
            return {"t": "str", "n": len(v), "r": v[:96] + ("…" if len(v) > 96 else "")}
        if isinstance(v, (bytes, bytearray)):
            return {"t": tn, "n": len(v)}
        if isinstance(v, type):
            return {"t": "type", "r": getattr(v, "__name__", tn)}
        shape = getattr(v, "shape", None)
        dtype = getattr(v, "dtype", None)
        if shape is not None and dtype is not None and not callable(shape):
            try:
                shp = [int(x) for x in shape]
            except Exception:
                shp = [str(shape)]
            d = {"t": tn, "shape": shp, "dtype": str(dtype)}
            dev = getattr(v, "device", None)
            if dev is not None:
                d["device"] = str(dev)
            rg = getattr(v, "requires_grad", None)
            if rg is not None:
                d["grad"] = bool(rg)          # True => a learned tensor, not just data
            try:
                d["head"] = _head(v)
            except Exception:
                pass
            return d
        if hasattr(v, "items") and hasattr(v, "keys"):
            items, n = {}, None
            try:
                n = len(v)
            except Exception:
                pass
            try:
                for i, (k, x) in enumerate(v.items()):
                    if i >= 24:
                        items["…"] = {"t": "…", "r": f"+{(n or 0) - 24} more keys"}
                        break
                    items[str(k)[:60]] = summarize(x, depth + 1, budget) if depth < 10 else {"t": type(x).__name__}
            except Exception:
                pass
            return {"t": tn, "n": n, "items": items}
        if isinstance(v, (list, tuple, set, frozenset, range)):
            seq = list(v) if isinstance(v, (set, frozenset)) else v
            head = []
            for i, x in enumerate(seq):
                if i >= 4:
                    break
                head.append(summarize(x, depth + 1, budget) if depth < 10 else {"t": type(x).__name__})
            return {"t": tn, "n": len(v), "head": head}
        if dataclasses.is_dataclass(v):
            fields = {}
            if depth < 7:
                for f in dataclasses.fields(v)[:16]:
                    fields[f.name] = summarize(getattr(v, f.name, None), depth + 1, budget)
            return {"t": tn, "fields": fields}
        try:
            dv = vars(v)
        except TypeError:
            dv = None
        if dv and depth < 5:
            attrs = {}
            for k, x in dv.items():
                if k.startswith("_"):
                    continue
                if len(attrs) >= 12:
                    attrs["…"] = {"t": "…"}
                    break
                attrs[k] = summarize(x, depth + 1, budget)
            out = {"t": tn, "attrs": attrs}
            # An nn.Module keeps its learned tensors in the underscore-prefixed
            # `_parameters` / `_buffers` dicts, which the loop above skips — so
            # without this a module's own weights (cognition tokens, embeddings,
            # norm scales) are invisible even though they are inputs to the
            # computation and shape its output. Submodules (`_modules`) are
            # deliberately NOT walked: that would unroll the whole network.
            if depth < 4:
                learned = {}
                for src, kind in ((getattr(v, "_parameters", None), "param"),
                                  (getattr(v, "_buffers", None), "buffer")):
                    if not isinstance(src, dict):
                        continue
                    for k, t in src.items():
                        if t is None or len(learned) >= 12:
                            continue
                        d2 = summarize(t, depth + 1, budget)
                        if isinstance(d2, dict):
                            d2["kind"] = kind
                        learned[k] = d2
                if learned:
                    out["params"] = learned
            return out
        r = _safe_repr(v)
        return {"t": tn, "r": r} if r is not None else {"t": tn}
    except Exception:
        return {"t": tn, "err": True}


def _fp(s):
    """Cheap identity of a summarized value — enough to tell 'it changed'.

    Compares shape/dtype for arrays and tensors (which is the thing worth
    watching as a value flows through `x = f(x); x = g(x)`), and type/len/repr
    for everything else. Deliberately not a deep compare: this runs inside the
    profile hook on every call a sampled function makes.
    """
    if not isinstance(s, dict):
        return repr(s)[:80]
    if "shape" in s:
        h = s.get("head")
        return (s.get("t"), tuple(s.get("shape") or ()), s.get("dtype"),
                tuple(h[:2]) if isinstance(h, list) else None)
    return (s.get("t"), s.get("n"), (s.get("r") or "")[:80])


def summarize_locals(f_locals):
    """Summarize a frame's locals, and SAY SO when anything is left out.

    Silent truncation is worse than none: the panel looked complete while the
    tail of a long function's locals was simply missing.
    """
    out, budget = {}, [NODE_BUDGET]
    items = [(k, v) for k, v in f_locals.items() if not k.startswith("__")]
    kept = 0
    for k, v in items:
        if kept >= MAX_LOCALS:
            out["\u2026"] = {"t": "\u2026",
                          "r": "+%d more names not captured" % (len(items) - kept)}
            break
        out[k] = summarize(v, 0, budget)
        kept += 1
        if budget[0] <= 0:
            out["\u2026"] = {"t": "\u2026",
                          "r": "summary budget reached; %d names not captured"
                               % (len(items) - kept)}
            break
    return out


# --------------------------------------------------------------------------
# call tracer
# --------------------------------------------------------------------------
class CallTracer:
    """Records (caller file, caller line, callee) for every in-project call.

    Frames that are not the project's own code (contextlib, dataclass-generated
    __init__, library callbacks) and module bodies are walked past, so an edge
    always points at the line that actually caused the call. What was skipped is
    remembered as `via`, and import-time work is tagged so it can be dropped.
    """

    def __init__(self, root: Path, roots: list[str], self_dir: Path):
        self.root = str(root)
        self.prefixes = tuple(os.path.join(str(root), r) for r in roots)
        self.self_dir = str(self_dir)
        self.main_file = ""      # the script/module run as __main__, set by run_target
        self.edges: dict[tuple, list] = {}
        self.calls: dict[tuple, list] = {}
        self.samples: dict[tuple, list] = {}   # tkey -> [{args, locals, ret, n}]
        self.pending: dict[int, dict] = {}     # live frame id -> partial sample
        # --- call-tree instances -------------------------------------------
        # `calls`/`edges` above are a call GRAPH: one entry per function, callers
        # merged. These build the call TREE alongside it: one instance per
        # (function, parent instance, calling line), so each call site is its own
        # card and the parent link is exact rather than reconstructed at render.
        self.insts: dict[tuple, int] = {}      # (tkey, parent, cline) -> inst id
        self.inst_meta: list = []              # inst id -> record
        self.frame_inst: dict[int, int] = {}   # live frame id -> inst id
        self.tkey_insts: dict[tuple, int] = {} # tkey -> instances created so far
        self.seq = count()
        self._orig_thread_start = None
        self._normalized_files = {}
        self._project_files = {}
        self.instance_edges = {}
        self._line_frames = {}
        self._previous_trace = None
        self._previous_thread_trace = None
        self._thread_traces = threading.local()
        self._active = False
        self.boundaries = BoundaryRecorder(
            root, self.frame_inst, lambda fn: self._inproj(self._norm(fn)), summarize, summarize_locals,
            max_samples=MAX_SAMPLES, context=lambda f: self.context(f) if hasattr(self, "context") else None,
            next_seq=self.seq.__next__,
            exclude=lambda fn: self._norm(fn).startswith(self.self_dir + os.sep),
        )

    def _norm(self, fn: str) -> str:
        cached = self._normalized_files.get(fn)
        if cached is not None:
            return cached
        normalized = fn if os.path.isabs(fn) else os.path.join(self.root, fn)
        if len(self._normalized_files) < 8192:
            self._normalized_files[fn] = normalized
        return normalized

    def _inproj(self, fn: str) -> bool:
        cached = self._project_files.get(fn)
        if cached is not None:
            return cached
        matched = not fn.startswith(self.self_dir) and any(
            fn == p or fn.startswith(p + os.sep) or fn == p + ".py"
            for p in self.prefixes
        )
        if len(self._project_files) < 8192:
            self._project_files[fn] = matched
        return matched

    def _real_frame(self, f):
        """Nearest in-project *named* caller frame, plus what we walked past."""
        via = None
        while f is not None:
            c = f.f_code
            n = c.co_name
            if n.startswith("<"):
                if n == "<module>":
                    if self._norm(c.co_filename) == self.main_file:
                        return f, via     # your script's top level: a real caller
                    if via is None:
                        via = "import"
                f = f.f_back
                continue
            fn = self._norm(c.co_filename)
            if not self._inproj(fn):
                if via is None:
                    base = os.path.basename(fn)
                    via = base[:-3] if base.endswith(".py") else base
                f = f.f_back
                continue
            return f, via
        return None, via

    def _profile(self, frame, event, arg):
        if not self._active:
            return
        self.boundaries.profile(frame, event, arg)
        if event == "return":
            inst = self.frame_inst.pop(id(frame), None)
            p = self.pending.pop(id(frame), None)
            if p is not None:
                p.pop("_fp", None)          # internal change-detector, not payload
                p["executed_lines"] = sorted(p.pop("_executed_lines", ()))
                status = self.boundaries._return_status(frame, arg)
                p["status"] = status
                try:
                    p["locals"] = summarize_locals(frame.f_locals)
                    if status == "returned":
                        p["ret"] = summarize(arg)
                    elif status == "suspended":
                        p["yielded"] = summarize(arg)
                    elif status == "raised":
                        p["ret_unavailable"] = "exceptional exit; this invocation did not return a value"
                    else:
                        p["ret_unavailable"] = "profile event could not distinguish suspension from exceptional exit"
                except Exception:
                    pass
                self.samples.setdefault(p.pop("tkey"), []).append(p)
            return
        if event != "call":
            return
        code = frame.f_code
        tfile = self._norm(code.co_filename)
        if not self._inproj(tfile):
            return
        tname = getattr(code, "co_qualname", code.co_name)
        leaf = tname.rsplit(".", 1)[-1]
        if leaf.startswith("<"):
            if leaf != "<module>" or tfile != self.main_file:
                if leaf != "<module>":
                    # Synthetic project frames share the enclosing card, but
                    # retain actual line events and observed calls from their body.
                    caller = frame.f_back
                    while caller is not None:
                        parent = self.frame_inst.get(id(caller))
                        if parent is not None:
                            self.frame_inst[id(frame)] = parent
                            break
                        caller = caller.f_back
                return  # comprehension / lambda / an imported module body
        s = next(self.seq)
        tkey = (tfile, tname, code.co_firstlineno)
        rec = self.calls.get(tkey)
        if rec is None:
            self.calls[tkey] = [1, s]
        else:
            rec[0] += 1
        # keep the values of the first few calls (module bodies excluded: too big)
        if leaf != "<module>" and self._want_sample(tkey, frame):
            try:
                self.pending[id(frame)] = {"tkey": tkey, "n": rec[0] if rec else 1,
                                           "line_scope": "frame_and_synthetic_children",
                                           "args": summarize_locals(frame.f_locals)}
            except Exception:
                pass
        # --- value timeline -------------------------------------------------
        # A name that is reassigned (`x = linear1(x); x = linear2(x)`) only ever
        # shows its FINAL value in the exit snapshot. To show the progression we
        # snapshot the *caller's* locals here, at each call it makes: by the time
        # linear2 is called, `x` already holds linear1's output. Entry args +
        # these steps + the exit locals give the whole sequence.
        # Bounded twice over: only for frames already being sampled (so the first
        # MAX_SAMPLES calls of a function), and at most MAX_STEPS snapshots each.
        cb = frame.f_back
        q = self.pending.get(id(cb)) if cb is not None else None
        if q is not None and len(q.get("steps", ())) < MAX_STEPS:
            try:
                snap = summarize_locals(cb.f_locals)
                prev = q.get("_fp")
                if prev is None:
                    prev = {k: _fp(v) for k, v in (q.get("args") or {}).items()}
                changed = {}
                for k, v in snap.items():
                    f = _fp(v)
                    if prev.get(k) != f:
                        changed[k] = v
                        prev[k] = f
                q["_fp"] = prev
                if changed:
                    q.setdefault("steps", []).append({"line": cb.f_lineno, "vars": changed})
            except Exception:
                pass

        b, via = self._real_frame(frame.f_back)
        if b is None:
            origin = getattr(threading.current_thread(), "_ct_origin", None)
            ekey = (origin + ("thread",) + tkey) if origin else (("", 0, "", 0, via or "") + tkey)
        else:
            bc = b.f_code
            ekey = (self._norm(bc.co_filename), b.f_lineno,
                    getattr(bc, "co_qualname", bc.co_name), bc.co_firstlineno,
                    via or "") + tkey
        rec = self.edges.get(ekey)
        if rec is None:
            self.edges[ekey] = [1, s]
        else:
            rec[0] += 1

        # --- call-tree instance ---------------------------------------------
        parent = self.frame_inst.get(id(b), -1) if b is not None else -1
        cline = b.f_lineno if b is not None else 0
        immediate = frame.f_back
        if immediate is not None and id(immediate) in self.frame_inst:
            parent = self.frame_inst[id(immediate)]
            cline = immediate.f_lineno
        ikey = (tkey, parent, cline)
        inst = self.insts.get(ikey)
        if inst is None:
            n_so_far = self.tkey_insts.get(tkey, 0)
            if n_so_far >= MAX_INSTANCES:
                # too many call sites (a logger, a norm layer): keep one merged
                # card for this function, exactly as the graph view did.
                inst = self.insts.setdefault((tkey, "merged", 0), len(self.inst_meta))
                if inst == len(self.inst_meta):
                    self.inst_meta.append({"tkey": tkey, "parent": -2, "cline": 0,
                                           "via": via or "", "count": 0, "seq": s,
                                           "merged": True})
                self.insts[ikey] = inst
            else:
                inst = len(self.inst_meta)
                self.insts[ikey] = inst
                self.tkey_insts[tkey] = n_so_far + 1
                self.inst_meta.append({"tkey": tkey, "parent": parent, "cline": cline,
                                       "via": via or "", "count": 0, "seq": s,
                                       "merged": False})
        self.inst_meta[inst]["count"] += 1
        self.inst_meta[inst].setdefault("executed_lines", set())
        self.inst_meta[inst].setdefault("executed_arcs", set())
        edge_key = (parent, inst, cline, via or "")
        edge = self.instance_edges.setdefault(edge_key, {"parent": parent, "to": inst,
            "cline": cline, "via": via or "", "count": 0, "seq": s})
        edge["count"] += 1
        self.frame_inst[id(frame)] = inst
        if id(frame) in self.pending:
            self.pending[id(frame)]["inst"] = inst

    def _want_sample(self, tkey, frame):
        """Extension point for bounded context-aware adapters."""
        return len(self.samples.get(tkey, ())) + sum(
            1 for q in self.pending.values() if q.get("tkey") == tkey
        ) < MAX_SAMPLES

    def _line_trace(self, frame, event, arg):
        """Compose line evidence with the existing coverage tracer.

        Only included project frames retain this local hook. Library internals
        keep coverage's own callback and do not acquire per-line capture work.
        """
        fid = id(frame)
        if not self._active:
            previous = (self._previous_trace if threading.current_thread() is threading.main_thread()
                        else getattr(self._thread_traces, "previous", self._previous_thread_trace))
            sys.settrace(previous)
            state = self._line_frames.pop(fid, None)
            local = state[0] if state else previous
            return local(frame, event, arg) if local else None
        if event == "call":
            previous = self._previous_trace
            if threading.current_thread() is not threading.main_thread():
                if not hasattr(self._thread_traces, "previous"):
                    previous = self._previous_thread_trace
                    local = previous(frame, event, arg) if previous else None
                    installed = sys.gettrace()
                    self._thread_traces.previous = installed if installed != self._line_trace else previous
                    sys.settrace(self._line_trace)
                else:
                    previous = self._thread_traces.previous
                    local = previous(frame, event, arg) if previous else None
            else:
                local = previous(frame, event, arg) if previous else None
            if not self._inproj(self._norm(frame.f_code.co_filename)):
                return local
            self._line_frames[fid] = [local, None]
            return self._line_trace
        state = self._line_frames.get(fid)
        if state is None:
            return None
        if state[0] is not None:
            state[0] = state[0](frame, event, arg)
        inst = self.frame_inst.get(fid)
        if inst is not None:
            record = self.inst_meta[inst]
            sample = self.pending.get(fid)
            if sample is None and frame.f_code.co_name.startswith("<"):
                caller = frame.f_back
                while caller is not None:
                    if self.frame_inst.get(id(caller)) != inst:
                        break
                    sample = self.pending.get(id(caller))
                    if sample is not None:
                        break
                    caller = caller.f_back
            if event == "line":
                line = frame.f_lineno
                record["executed_lines"].add(line)
                if state[1] is not None:
                    record["executed_arcs"].add((state[1], line))
                state[1] = line
                if sample is not None:
                    sample.setdefault("_executed_lines", set()).add(line)
            elif event == "exception":
                if sample is not None:
                    kind = arg[0].__module__ + "." + arg[0].__name__
                    sample.setdefault("exception_types", {})[kind] = sample.get("exception_types", {}).get(kind, 0) + 1
        if event == "return":
            self._line_frames.pop(fid, None)
        return self._line_trace

    def start(self):
        tracer = self
        previous = sys.gettrace()
        if type(previous).__module__.startswith("coverage") and type(previous).__name__ == "CTracer":
            raise RuntimeError("CallTracer context lines require coverage.Coverage(timid=True); CTracer replaces the composed line hook")

        orig = threading.Thread.start
        self._orig_thread_start = orig

        def start_with_origin(self):
            f, _ = tracer._real_frame(sys._getframe(1))
            if f is not None:
                c = f.f_code
                self._ct_origin = (tracer._norm(c.co_filename), f.f_lineno,
                                   getattr(c, "co_qualname", c.co_name), c.co_firstlineno)
            return orig(self)

        threading.Thread.start = start_with_origin
        self._active = True
        self._previous_trace = sys.gettrace()
        self._previous_thread_trace = getattr(threading, "_trace_hook", None)
        threading.settrace(self._line_trace)
        sys.settrace(self._line_trace)
        threading.setprofile(self._profile)
        sys.setprofile(self._profile)

    def stop(self):
        self._active = False
        sys.setprofile(None)
        threading.setprofile(None)
        sys.settrace(self._previous_trace)
        threading.settrace(self._previous_thread_trace)
        if self._orig_thread_start is not None:
            threading.Thread.start = self._orig_thread_start

    def dump(self, path: Path):
        def rel(p):
            if not p:
                return ""
            try:
                return os.path.relpath(p, self.root)
            except ValueError:
                return p

        data = {
            "root": self.root,
            "main_file": rel(self.main_file),
            "calls": [
                {"file": rel(k[0]), "name": k[1], "first": k[2], "count": v[0], "seq": v[1],
                 "samples": self.samples.get(k, [])}
                for k, v in self.calls.items()
            ],
            "instances": [
                {"file": rel(m["tkey"][0]), "name": m["tkey"][1], "first": m["tkey"][2],
                 "parent": m["parent"], "cline": m["cline"], "via": m["via"],
                 "count": m["count"], "seq": m["seq"], "merged": m["merged"]}
                | {"executed_lines": sorted(m.get("executed_lines", ())),
                   "executed_arcs": sorted(m.get("executed_arcs", ()))}
                for m in self.inst_meta
            ],
            "edges": [
                {"cfile": rel(k[0]), "cline": k[1], "cname": k[2], "cfirst": k[3], "via": k[4],
                 "tfile": rel(k[5]), "tname": k[6], "tfirst": k[7], "count": v[0], "seq": v[1]}
                for k, v in self.edges.items()
            ],
        }
        data["instance_edges"] = list(self.instance_edges.values())
        data["line_capture"] = {"schema": 1, "scope": "call_site_group",
            "note": "Union of observed line events within each calling context; sampled invocations also retain their own line events. Merged helpers are explicitly marked."}
        data.update(self.boundaries.dump())
        path.write_text(json.dumps(data))
        return len(data["calls"]), len(data["edges"])


# --------------------------------------------------------------------------
# running the target
# --------------------------------------------------------------------------
class Tee(io.TextIOBase):
    def __init__(self, stream, sink):
        self.stream, self.sink = stream, sink

    def write(self, s):
        self.sink.write(s)
        return self.stream.write(s)

    def flush(self):
        self.sink.flush()
        self.stream.flush()

    def isatty(self):
        return getattr(self.stream, "isatty", lambda: False)()

    # Targets that re-open their own stdout by descriptor -- e.g.
    # `sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)` -- need the
    # underlying fd.  io.TextIOBase.fileno() raises io.UnsupportedOperation, which
    # aborts such a target at import time before anything is traced.  Delegate
    # instead.  Consequence: once the target rebinds sys.stdout to that fd, the Tee
    # is out of the loop and run.log stops receiving output; capture stdout at the
    # shell instead.
    def fileno(self):
        return self.stream.fileno()

    def writable(self):
        return True


def run_target(argv: list[str], tracer=None) -> int:
    """Run argv in-process, the way `python <argv>` would."""
    argv = list(argv)
    if argv and argv[0] in ("python", "python3") or (argv and Path(argv[0]).name.startswith("python")):
        argv = argv[1:]  # `python -m pkg ...` -> `-m pkg ...`
    if not argv:
        raise SystemExit("codetrace: nothing to run after --")

    try:
        if argv[0] == "-m":
            if len(argv) < 2:
                raise SystemExit("codetrace: -m needs a module name")
            # `python -m pkg` puts the working directory first on sys.path
            sys.path.insert(0, os.getcwd())
            sys.argv = [argv[1]] + argv[2:]
            if tracer is not None:
                import importlib.util
                try:
                    spec = importlib.util.find_spec(argv[1])
                    origin = getattr(spec, "origin", None)
                    if spec and spec.submodule_search_locations and not origin:
                        origin = os.path.join(list(spec.submodule_search_locations)[0], "__main__.py")
                    elif spec and spec.submodule_search_locations:
                        origin = os.path.join(list(spec.submodule_search_locations)[0], "__main__.py")
                    if origin:
                        tracer.main_file = os.path.abspath(origin)
                except Exception:
                    pass
            runpy.run_module(argv[1], run_name="__main__", alter_sys=True)
        else:
            prog = argv[0]
            p = Path(prog)
            if not p.is_file():          # a same-named *directory* must not win over PATH
                found = shutil.which(prog)
                if not found:
                    raise SystemExit(f"codetrace: cannot find {prog!r} as a file or on PATH")
                p = Path(found)
            # `python script.py` puts the script's own directory first
            sys.path.insert(0, str(p.resolve().parent))
            sys.argv = [str(p)] + argv[1:]
            if tracer is not None:
                tracer.main_file = str(p.resolve())
            runpy.run_path(str(p), run_name="__main__")
    except SystemExit as ex:
        c = ex.code
        return 0 if c is None else (c if isinstance(c, int) else 1)
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        prog="codetrace",
        description="Run a Python command once and draw what actually executed.",
        epilog="Put the command after --, e.g.  codetrace.py -- python -m yourpkg.cli --flag",
    )
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--out", default="codetrace_out", help="output directory")
    ap.add_argument("--include", action="append", default=[],
                    help="source dir/file to treat as yours, relative to root (repeatable; "
                         "default: auto-detect top-level packages)")
    ap.add_argument("--title", default=None, help="page title (default: the project dir name)")
    ap.add_argument("--brand", default=None, help="small label above the command line")
    ap.add_argument("--entry", default=None,
                    help="qualified name of the entry function (default: the function that "
                         "reaches the most others, which is normally your main)")
    ap.add_argument("--label", default=None, help="text for the outcome badge (default: exit code + duration)")
    ap.add_argument("--keep-imports", action="store_true",
                    help="keep functions that only ran while importing modules (default: drop them)")
    ap.add_argument("--max-gap", type=int, default=300,
                    help="how far (px) a callee may drop to sit level with its call site")
    ap.add_argument("--important", action="append", default=[], metavar="PATTERN",
                    help="highlight functions matching this glob as the repo's core contribution: "
                         "'name', 'Class.method', 'path/glob.py:name' (repeatable)")
    ap.add_argument("--important-file", default=None, metavar="FILE",
                    help="file with one --important pattern per line (# comments ok). "
                         "Default: codetrace_important.txt in --root if it exists")
    ap.add_argument("--no-values", action="store_true",
                    help="do not record argument/local/return values (smaller page, less overhead)")
    ap.add_argument("--no-mosaic", action="store_true", help="skip the file mosaic page")
    ap.add_argument("--rebuild", action="store_true",
                    help="do not run anything: rebuild the pages from the callgraph.json / coverage.json "
                         "already in --out (after editing importance patterns, --entry, --max-gap, ...)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- then the command to run")
    args = ap.parse_args()

    argv = args.cmd
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv and not args.rebuild:
        ap.error("nothing to run: put the command after --")

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    roots = args.include or autodetect_roots(root)
    if not roots:
        ap.error(f"no Python found under {root}; pass --include")

    try:
        import coverage  # noqa
    except ImportError:
        print("codetrace: needs coverage —  pip install coverage", file=sys.stderr)
        return 2

    print(f"codetrace: root={root}")
    print(f"codetrace: watching {', '.join(roots)}"
          + ("" if args.include else "   (override with --include)"))
    os.chdir(root)

    cg_json, cov_json = out / "callgraph.json", out / "coverage.json"
    meta_json = out / "run.json"
    if args.rebuild:
        if not (cg_json.exists() and cov_json.exists()):
            print(f"codetrace: --rebuild needs {cg_json} and {cov_json}", file=sys.stderr)
            return 2
        meta = json.loads(meta_json.read_text()) if meta_json.exists() else {}
        command, code, secs = meta.get("command", "(earlier run)"), meta.get("exit", 0), meta.get("secs", 0.0)
        print(f"codetrace: rebuilding from the earlier run of {command}")
        return build_pages(args, root, out, roots, cg_json, cov_json, command, code, secs)

    print(f"codetrace: running {' '.join(argv)}\n", flush=True)
    log_path = out / "run.log"
    log = log_path.open("w", errors="replace")
    if args.no_values:
        global MAX_SAMPLES
        MAX_SAMPLES = 0
    tracer = CallTracer(root, roots, HERE)

    cov = coverage.Coverage(
        branch=True, cover_pylib=False, concurrency="thread", timid=True,
        data_file=str(out / ".coverage"),
        include=[pat for r in roots
                 for pat in ([str(root / r)] if (root / r).is_file()
                             else [str(root / r / "*"), str(root / r)])],
    )
    cov._warn_no_data = False
    cov._warn_unimported_source = False
    t0 = time.time()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(old_out, log), Tee(old_err, log)
    cov.start()
    tracer.start()
    try:
        code = run_target(argv, tracer)
    except BaseException as ex:            # target blew up: still draw what ran
        tracer.stop(); cov.stop()
        sys.stdout, sys.stderr = old_out, old_err
        log.close()
        import traceback
        traceback.print_exc()
        print(f"\ncodetrace: target raised {type(ex).__name__}; drawing the partial run", file=sys.stderr)
        code = 1
    else:
        tracer.stop(); cov.stop()
        sys.stdout, sys.stderr = old_out, old_err
        log.close()
    secs = time.time() - t0

    cov.save()
    try:
        cov.json_report(outfile=str(cov_json), show_contexts=False)
    except Exception as ex:                # nothing measured
        print(f"codetrace: coverage report failed ({ex}); writing empty", file=sys.stderr)
        cov_json.write_text('{"files": {}}')

    nfun, nedge = tracer.dump(cg_json)
    print(f"\ncodetrace: traced {nfun} functions, {nedge} call edges in {secs:.1f}s (exit {code})")
    command = " ".join(argv)
    meta_json.write_text(json.dumps({"command": command, "exit": code, "secs": round(secs, 2)}))
    return build_pages(args, root, out, roots, cg_json, cov_json, command, code, secs)


def build_pages(args, root, out, roots, cg_json, cov_json, command, code, secs) -> int:
    label = args.label or f"exit {code} · {secs:.1f}s"
    title = args.title or root.name
    brand = args.brand or f"{root.name} · call tree with line coverage"

    sys.path.insert(0, str(HERE))
    import _calltree, _mosaic, _render

    patterns = list(args.important)
    imp_file = Path(args.important_file) if args.important_file else (root / "codetrace_important.txt")
    if imp_file.exists():
        patterns += imp_file.read_text().splitlines()
        print(f"codetrace: importance patterns from {imp_file}")

    payload = _calltree.build(
        root=root, cg=json.loads(cg_json.read_text()), cov=json.loads(cov_json.read_text()),
        command=command, outcome=label, title=title, brand=brand,
        entry=args.entry, drop_imports=not args.keep_imports, max_gap=args.max_gap,
        important=patterns,
    )
    if patterns:
        print(f"codetrace: {payload['totals']['important']} functions marked important")
    (out / "payload_call_tree.json").write_text(json.dumps(payload, separators=(",", ":")))
    _render.render(HERE / "templates" / "call_tree.html", payload, out / "call-tree.html")

    if not args.no_mosaic:
        mp = _mosaic.build(
            root=root, roots=roots, cov=json.loads(cov_json.read_text()),
            command=command, outcome=label, title=title, brand=brand.replace("call tree with ", ""),
        )
        (out / "payload_mosaic.json").write_text(json.dumps(mp, separators=(",", ":")))
        _render.render(HERE / "templates" / "mosaic.html", mp, out / "mosaic.html")

    print(f"codetrace: open {out / 'call-tree.html'}")
    if not args.no_mosaic:
        print(f"codetrace: open {out / 'mosaic.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
