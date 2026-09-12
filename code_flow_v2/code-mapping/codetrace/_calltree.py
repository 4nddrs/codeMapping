"""Turn a recorded call graph + coverage into a laid-out call tree.

Cards are functions (AST-extracted, full source). A card sits one column right
of whoever called it first, level with the call-site row when that is close.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

LH, HDR, CHW, GUT = 17, 44, 7.31, 67
RET = 20   # the '↩ return' strip at the foot of every card
COL_GAP, ROW_GAP = 150, 28
MIN_W, MAX_W = 380, 1000


class _Defs(ast.NodeVisitor):
    """Every def in a file, keyed by qualified name, as (start, def_line, end).

    `start` includes decorator lines because that is what a code object reports
    as co_firstlineno, which is how the tracer identifies a function.
    """

    def __init__(self):
        self.stack, self.out = [], {}

    def _add(self, node):
        qual = ".".join(self.stack + [node.name])
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        self.out.setdefault(qual, []).append((start, node.lineno, node.end_lineno))

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self._add(node)
        self.stack.append(node.name)
        self.stack.append("<locals>")
        self.generic_visit(node)
        self.stack.pop()
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef


def pretty_via(v: str) -> str:
    if not v:
        return ""
    if "<string>" in v:
        return "generated __init__"
    if "importlib" in v or v == "import":
        return "import"
    return v.rsplit("/", 1)[-1]


def _is_important(rel, name, patterns):
    """patterns: 'name-glob' or 'file-glob:name-glob' (fnmatch, case-sensitive)."""
    import fnmatch
    for pat in patterns:
        pat = pat.strip()
        if not pat or pat.startswith("#"):
            continue
        if ":" in pat:
            fp, np_ = pat.split(":", 1)
            if fnmatch.fnmatch(rel, fp) and (fnmatch.fnmatch(name, np_) or fnmatch.fnmatch(name.rsplit(".", 1)[-1], np_)):
                return True
        elif fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(name.rsplit(".", 1)[-1], pat) or fnmatch.fnmatch(rel + ":" + name, pat):
            return True
    return False


_HEADING = re.compile(r"#\s*-{3,}\s+(.+)")


def _workflow_from_important(patterns, nodes):
    """`# --- heading` comments in important.txt become jump targets.

    Each heading maps to the earliest-seq card that matches a pattern in that
    section. Sections with no matching card are dropped — a dead option would
    look like the stage exists when the run never reached it.
    """
    stages, heading, pats = [], None, []

    def flush():
        nonlocal heading, pats
        if heading and pats:
            for n in sorted(nodes.values(), key=lambda x: x["seq"]):
                if _is_important(n["file"], n["name"], pats):
                    stages.append({"label": heading, "name": n["name"]})
                    break
        heading, pats = None, []

    for raw in patterns:
        line = raw.strip()
        m = _HEADING.match(line)
        if m:
            flush()
            heading = m.group(1).strip()
            continue
        if not line or line.startswith("#"):
            continue
        if heading:
            pats.append(line)
    flush()
    return stages


def build(*, root: Path, cg, cov, command, outcome, title, brand,
          entry=None, drop_imports=True, max_gap=300, important=()):
    main_file = cg.get("main_file") or ""   # the script/module run as __main__
    # ---------- read every source file the trace touched ----------
    defs, sources = {}, {}
    files = {c["file"] for c in cg["calls"]} | {e["cfile"] for e in cg["edges"] if e["cfile"]}
    for rel in sorted(files):
        p = root / rel
        if not p.exists():
            continue
        src = p.read_text(errors="replace")
        sources[rel] = src.split("\n")
        v = _Defs()
        try:
            v.visit(ast.parse(src))
        except SyntaxError:
            continue
        defs[rel] = v.out

    # Reverse index: (file, co_firstlineno) -> qualified name. Needed on
    # Python < 3.11, where code objects have no `co_qualname` and the tracer
    # can only record the bare `co_name` ("__init__", "step", ...). The bare
    # name never matches _Defs' qualified keys, so without this every method
    # would be dropped. Line numbers still identify the function uniquely.
    by_line = {}
    for rel, table in defs.items():
        for qual, spans in table.items():
            for s, d, e in spans:
                by_line.setdefault((rel, s), qual)
                by_line.setdefault((rel, d), qual)

    def qualify(rel, qual, first):
        """Recover the qualified name when the tracer only saw a bare one."""
        if qual in defs.get(rel, {}):
            return qual
        return by_line.get((rel, first), qual)

    def locate(rel, qual, first):
        cands = defs.get(rel, {}).get(qual, [])
        if not cands:
            cands = defs.get(rel, {}).get(qualify(rel, qual, first), [])
        for s, d, e in cands:
            if s == first or d == first:
                return s, d, e
        return min(cands, key=lambda t: abs(t[0] - first)) if cands else None

    # ---------- coverage, keyed repo-relative ----------
    cov_files = {}
    for k, v in (cov.get("files") or {}).items():
        kp = Path(k)
        try:
            rel = kp.resolve().relative_to(root).as_posix() if kp.is_absolute() else kp.as_posix()
        except ValueError:
            continue
        cov_files[rel] = v

    # ---------- one card per CALL SITE (call tree), when the trace has it -----
    # `calls`/`edges` are a call GRAPH: every caller of a function merges into one
    # card. That merges distinct invocations — BasePolicy.get_action runs once as
    # the sim wrapper and once as the policy — so one card carries both
    # invocations' out-edges and the second entry becomes a back-edge looping onto
    # the card you just came from.
    #
    # `instances` is the call TREE the tracer records from the live stack: one
    # entry per (function, parent instance, calling line) with an exact parent.
    # Parents are always created before their children, so it is acyclic by
    # construction — unlike a first_caller graph rebuilt at render time.
    insts = cg.get("instances")
    nodes, edges, first_caller = {}, [], {}
    if insts:
        # samples are recorded per function; each carries the instance it came from
        by_inst = {}
        for c in cg["calls"]:
            for smp in (c.get("samples") or []):
                if "inst" in smp:
                    by_inst.setdefault(smp["inst"], []).append(smp)

        inst_node = {}          # instance index -> node id
        dropped_inst = set()    # instances with no card (module bodies, unlocatable)
        for idx, m in enumerate(insts):
            mfile, mname, mfirst = m["file"], m["name"], m["first"]
            is_main_body = mname == "<module>" and mfile == main_file
            if mname == "<module>" and not is_main_body:
                dropped_inst.add(idx)          # an imported module body
                continue
            if is_main_body:
                if mfile not in sources:
                    dropped_inst.add(idx)
                    continue
                st, df, en = 1, 1, len(sources[mfile])
            else:
                loc = locate(mfile, mname, mfirst)
                if not loc:
                    dropped_inst.add(idx)
                    continue
                st, df, en = loc
            lines = sources[mfile][st - 1:en]
            cv = cov_files.get(mfile, {})
            ex = sorted(x for x in cv.get("executed_lines", []) if st <= x <= en)
            mi = sorted(x for x in cv.get("missing_lines", []) if st <= x <= en)
            exs = set(ex)
            part = sorted({b[0] for b in (cv.get("missing_branches") or []) if b and b[0] in exs})
            maxlen = max((len(l) for l in lines), default=0)
            nid_ = len(nodes)
            inst_node[idx] = nid_
            disp = "__main__" if is_main_body else qualify(mfile, mname, mfirst)
            nodes[nid_] = {
                "id": nid_, "file": mfile, "name": disp,
                "start": st, "def": df, "end": en,
                "src": "\n".join(lines), "nlines": len(lines),
                "ex": ex, "mi": mi, "partial": part,
                "calls": m["count"], "seq": m["seq"],
                "w": max(MIN_W, min(MAX_W, round(GUT + maxlen * CHW + 26))),
                "h": HDR + len(lines) * LH + RET,
                "samples": by_inst.get(idx, []),
                "important": _is_important(mfile, disp, important),
            }
            if m.get("via"):
                nodes[nid_]["via"] = pretty_via(m["via"])

        def nearest_drawn_ancestor(idx):
            """Skip past module bodies / unlocatable frames to the nearest card."""
            seen = 0
            p = insts[idx]["parent"]
            while p is not None and p >= 0 and seen < 10000:
                if p in inst_node:
                    return p
                p = insts[p]["parent"]
                seen += 1
            return None

        # A thread's first frame has nothing above it on its own stack, so its
        # instance is recorded with parent -1, like the run's root, and the thread
        # (e.g. a server started beside its client) would split off the tree. The
        # graph edge the tracer also writes (via "thread") names the function and
        # line that called .start(): hang the thread body under that function's
        # latest card from before the thread began, on that line.
        thread_origin = {}
        for e in cg.get("edges") or []:
            if e.get("via") == "thread" and e.get("cfile"):
                thread_origin.setdefault((e["tfile"], e["tname"], e["tfirst"]), e)
        fn_insts = {}
        for j, mj in enumerate(insts):
            if j in inst_node:
                fn_insts.setdefault((mj["file"], mj["name"], mj["first"]), []).append(j)

        def thread_parent(idx):
            m = insts[idx]
            e = thread_origin.get((m["file"], m["name"], m["first"]))
            if e is None:
                return None
            before = [j for j in fn_insts.get((e["cfile"], e["cname"], e["cfirst"]), ())
                      if insts[j]["seq"] <= m["seq"]]
            return (max(before, key=lambda j: insts[j]["seq"]), e["cline"]) if before else None

        for idx, m in enumerate(insts):
            n = inst_node.get(idx)
            if n is None:
                continue
            par = m["parent"]
            if par == -1:
                tp = thread_parent(idx)
                if tp is None:
                    continue                   # the run's own root
                c, cline = inst_node[tp[0]], tp[1]
                edges.append({"from": c, "line": cline, "to": n,
                              "n": m["count"], "seq": m["seq"], "via": "thread"})
                if n not in first_caller and c != n:
                    first_caller[n] = (c, cline, m["seq"])
                continue
            if par == -2:
                continue                       # merged hot helper: wired below
            anc = par if par in inst_node else nearest_drawn_ancestor(idx)
            if anc is None:
                # only reachable by importing a module — same rule as the graph path
                if drop_imports:
                    nodes.pop(n, None)
                    inst_node.pop(idx, None)
                continue
            c = inst_node[anc]
            edges.append({"from": c, "line": m["cline"], "to": n,
                          "n": m["count"], "seq": m["seq"], "via": pretty_via(m.get("via", ""))})
            if n not in first_caller and c != n:
                first_caller[n] = (c, m["cline"], m["seq"])

        # merged instances have many call sites and no single parent; wire them
        # from the graph edges, exactly as the merged (graph) view did.
        merged = {idx: inst_node[idx] for idx, m in enumerate(insts)
                  if m["parent"] == -2 and idx in inst_node}
        if merged:
            fn_nodes = {}
            for idx, nid_ in inst_node.items():
                key = (insts[idx]["file"], insts[idx]["name"], insts[idx]["first"])
                fn_nodes.setdefault(key, []).append(nid_)
            for idx, tgt in merged.items():
                tkey = (insts[idx]["file"], insts[idx]["name"], insts[idx]["first"])
                for e in cg["edges"]:
                    if (e["tfile"], e["tname"], e["tfirst"]) != tkey:
                        continue
                    if not e["cfile"]:
                        continue
                    for src in fn_nodes.get((e["cfile"], e["cname"], e["cfirst"]), []):
                        if src == tgt:
                            continue
                        edges.append({"from": src, "line": e["cline"], "to": tgt,
                                      "n": e["count"], "seq": e["seq"],
                                      "via": pretty_via(e.get("via", ""))})
                        # never let a merged node become its own ancestor
                        if tgt not in first_caller:
                            walk, hop, ok = src, 0, True
                            while walk is not None and hop < 10000:
                                if walk == tgt:
                                    ok = False
                                    break
                                fc = first_caller.get(walk)
                                walk = fc[0] if fc else None
                                hop += 1
                            if ok:
                                first_caller[tgt] = (src, e["cline"], e["seq"])
    else:
        # ---------- one card per function ----------
        nodes, nid = {}, {}
        for c in sorted(cg["calls"], key=lambda c: c["seq"]):
            is_main_body = c["name"] == "<module>" and c["file"] == main_file
            if c["name"] == "<module>" and not is_main_body:
                continue
            if is_main_body:
                if c["file"] not in sources:
                    continue
                s, d, e = 1, 1, len(sources[c["file"]])
            else:
                loc = locate(c["file"], c["name"], c["first"])
                if not loc:
                    continue
                s, d, e = loc
            lines = sources[c["file"]][s - 1:e]
            cv = cov_files.get(c["file"], {})
            ex = sorted(x for x in cv.get("executed_lines", []) if s <= x <= e)
            mi = sorted(x for x in cv.get("missing_lines", []) if s <= x <= e)
            exs = set(ex)
            part = sorted({b[0] for b in (cv.get("missing_branches") or []) if b and b[0] in exs})
            maxlen = max((len(l) for l in lines), default=0)
            i = len(nodes)
            nid[(c["file"], c["name"], c["first"])] = i
            disp = "__main__" if is_main_body else qualify(c["file"], c["name"], c["first"])
            nodes[i] = {
                "id": i, "file": c["file"],
                "name": disp,
                "start": s, "def": d, "end": e,
                "src": "\n".join(lines), "nlines": len(lines),
                "ex": ex, "mi": mi, "partial": part,
                "calls": c["count"], "seq": c["seq"],
                "w": max(MIN_W, min(MAX_W, round(GUT + maxlen * CHW + 26))),
                "h": HDR + len(lines) * LH + RET,
                "samples": c.get("samples") or [],
                "important": _is_important(c["file"], disp, important),
            }

        # ---------- edges ----------
        edges, first_caller = [], {}
        for e in sorted(cg["edges"], key=lambda e: e["seq"]):
            t = nid.get((e["tfile"], e["tname"], e["tfirst"]))
            if t is None:
                continue
            via = pretty_via(e.get("via", ""))
            from_main_body = e["cname"] == "<module>" and e["cfile"] == main_file
            if not e["cfile"] or (e["cname"] == "<module>" and not from_main_body):
                if via and "via" not in nodes[t]:
                    nodes[t]["via"] = via
                continue
            c = nid.get((e["cfile"], e["cname"], e["cfirst"]))
            if c is None:
                continue
            if drop_imports and via == "import":
                continue  # reached only by importing a module, not by the run itself
            edges.append({"from": c, "line": e["cline"], "to": t,
                          "n": e["count"], "seq": e["seq"], "via": via})
            if t not in first_caller and c != t:
                first_caller[t] = (c, e["cline"], e["seq"])

    if not nodes:
        raise SystemExit("codetrace: nothing of yours ran — check --include / the command")

    # ---------- entry: the function that reaches the most others ----------
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], set()).add(e["to"])

    def reach_from(i):
        seen, stack = set(), [i]
        while stack:
            j = stack.pop()
            if j in seen:
                continue
            seen.add(j)
            stack.extend(adj.get(j, ()))
        return seen

    if entry:
        cand = [i for i, n in nodes.items() if n["name"] == entry or f"{n['file']}:{n['name']}" == entry]
        if not cand:
            cand = [i for i, n in nodes.items() if n["name"].endswith("." + entry)]
        if not cand:
            raise SystemExit(f"codetrace: --entry {entry!r} did not match any traced function")
        entry_id = min(cand, key=lambda i: nodes[i]["seq"])
        reach = reach_from(entry_id)
    else:
        best, entry_id, reach = -1, None, set()
        for i in nodes:
            r = reach_from(i)
            if len(r) > best or (len(r) == best and nodes[i]["seq"] < nodes[entry_id]["seq"]):
                best, entry_id, reach = len(r), i, r

    dropped = len(nodes) - len(reach)
    nodes = {i: n for i, n in nodes.items() if i in reach}
    edges = [e for e in edges if e["from"] in reach and e["to"] in reach]
    first_caller = {k: v for k, v in first_caller.items() if k in reach and v[0] in reach}
    nodes[entry_id]["via"] = "entry point"

    # ---------- depth = distance along first-call edges ----------
    depth = {}

    def get_depth(i, guard=0):
        if i in depth:
            return depth[i]
        fc = first_caller.get(i)
        depth[i] = 0 if (fc is None or guard > 500) else get_depth(fc[0], guard + 1) + 1
        return depth[i]

    for i in nodes:
        get_depth(i)

    ncols = max(depth.values()) + 1
    col_w = [MIN_W] * ncols
    for i, n in nodes.items():
        col_w[depth[i]] = max(col_w[depth[i]], n["w"])
    col_x, x = [], 0
    for w in col_w:
        col_x.append(x)
        x += w + COL_GAP

    # ---------- placement ----------
    col_bottom = [0] * ncols
    order = sorted(nodes, key=lambda i: (0 if i == entry_id else 1, nodes[i]["seq"]))
    placed = set()
    for i in order:
        n, d = nodes[i], depth[i]
        fc = first_caller.get(i)
        if fc and fc[0] in placed:
            cn = nodes[fc[0]]
            want = min(cn["y"] + HDR + (fc[1] - cn["start"]) * LH - HDR // 2,
                       col_bottom[d] + max_gap)
        else:
            want = col_bottom[d]
        y = max(want, col_bottom[d])
        n["x"], n["y"], n["col"], n["w"] = col_x[d], y, d, col_w[d]
        col_bottom[d] = y + n["h"] + ROW_GAP
        placed.add(i)

    entry_name = nodes[entry_id]["name"]
    return {
        "title": title,
        "brand": brand,
        "command": command,
        "outcome": outcome,
        "entry_label": f"{entry_name} — where this run starts",
        "geom": {"LH": LH, "HDR": HDR, "ncols": ncols,
                 "world_w": col_x[-1] + col_w[-1], "world_h": max(col_bottom)},
        "totals": {
            "functions": len(nodes),
            "edges": len(edges),
            "calls": sum(n["calls"] for n in nodes.values()),
            "lines": sum(n["nlines"] for n in nodes.values()),
            "executed": sum(len(n["ex"]) for n in nodes.values()),
            "columns": ncols,
            "dropped": dropped,
            "important": sum(1 for n in nodes.values() if n["important"]),
            "sampled": sum(1 for n in nodes.values() if n["samples"]),
        },
        "main": entry_id,
        "nodes": [nodes[i] for i in sorted(nodes)],
        "edges": edges,
        "workflow": _workflow_from_important(important, nodes),
    }
