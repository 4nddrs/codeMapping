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


_NONE_SUSPENSION_NOTE = (
    "The saved profiler event cannot distinguish yield None from generator.close() "
    "or generator.throw(); this sample's outcome is unknown."
)


def _normalize_sample_outcome(sample):
    """Interpret an ambiguous legacy profile result without changing raw evidence."""
    value = sample.get("yielded")
    is_none = value is None or isinstance(value, dict) and value.get("t") == "NoneType"
    if sample.get("status") != "suspended" or "yielded" not in sample or not is_none:
        return sample
    normalized = dict(sample)
    normalized.pop("yielded")
    normalized["status"] = "unknown"
    normalized["ret_unavailable"] = _NONE_SUSPENSION_NOTE
    normalized["outcome_provenance"] = {
        "raw_status": sample["status"], "raw_field": "yielded", "raw_value": value,
        "note": "Conservative interpretation of a saved profile event; raw capture was not modified.",
    }
    return normalized


def _boundary_outcomes(record, capture):
    outcomes = dict(record.get("outcomes") or {})
    if capture.get("none_suspension_outcomes") == "unknown" or not outcomes.get("suspended"):
        return outcomes, None
    raw = dict(outcomes)
    # First-N samples cannot reveal the outcome split for all other entries.
    # Keep the entire aggregate count in a broad, truthful legacy category.
    outcomes["suspension_or_exception"] = outcomes.pop("suspended")
    return outcomes, {
        "raw_outcomes": raw,
        "note": "Legacy suspension counts may include generator.close() or throw(); the full outcome split cannot be recovered from bounded samples.",
    }


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
                    stages.append({"label": heading, "name": n["name"], "id": n["id"], "file": n["file"]})
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


def validate_innovation(spec):
    """Check an innovation.json spec on its own, before any card exists.

    Raises ValueError naming the entry: the spec is not an object with a
    `functions` list, an entry lacks file/function, a function is listed twice,
    `role` is not core/supporting, `ranges` is empty, or a range lacks integer
    1-based start <= end or a `what`. Returns the spec unchanged.
    """
    if not isinstance(spec, dict) or not isinstance(spec.get("functions"), list):
        raise ValueError("innovation spec must be a JSON object with a 'functions' list")
    seen = set()
    for i, entry in enumerate(spec["functions"]):
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k] for k in ("file", "function")):
            raise ValueError(f"innovation functions[{i}]: needs 'file' and 'function' as non-empty strings")
        key = (entry["file"], entry["function"])
        where = f"innovation {key[0]}:{key[1]}"
        if key in seen:
            raise ValueError(f"{where}: listed more than once; put all its ranges in one entry")
        seen.add(key)
        if entry.get("role") not in ("core", "supporting"):
            raise ValueError(f"{where}: role must be 'core' or 'supporting', not {entry.get('role')!r}")
        if not isinstance(entry.get("ranges"), list) or not entry["ranges"]:
            raise ValueError(f"{where}: ranges must list at least one {{start, end, what}}")
        for span in entry["ranges"]:
            ints = isinstance(span, dict) and all(
                isinstance(span.get(k), int) and not isinstance(span.get(k), bool) for k in ("start", "end"))
            if not ints or not 1 <= span["start"] <= span["end"]:
                raise ValueError(f"{where}: each range needs integer 1-based start <= end, got {span!r}")
            if not isinstance(span.get("what"), str) or not span["what"].strip():
                raise ValueError(f"{where}: lines {span['start']}-{span['end']} need a 'what'")
    return spec


def apply_innovation(payload, spec):
    """Frame the cards that implement the studied contribution (innovation.json).

    See schemas/innovation.schema.md. After validate_innovation(), each card of a
    listed function gets `innovation` with the ranges that lie inside it,
    which the viewer draws as a green frame (dashed for role "supporting") with
    green gutter marks on the ranges. A listed function with no card is reported
    in payload["innovation"]["unmatched"]. Ranges that fit none of the function's
    cards, or a `text` that no longer matches the source, raise ValueError,
    because stale line numbers would mark the wrong code. Runs after build(), so
    layout, coverage and edges are untouched.
    """
    validate_innovation(spec)
    nodes, marked, unmatched = payload["nodes"], set(), []
    for entry in spec["functions"]:
        key = (entry["file"], entry["function"])
        where = f"innovation {key[0]}:{key[1]}"
        cards = [n for n in nodes if (n["file"], n["name"]) == key and not n.get("boundary")]
        if not cards:
            unmatched.append(f"{key[0]}:{key[1]}")
            continue
        # Same-named cards can show different source (a property getter and its
        # setter): fit each range on its own and frame each card with the ranges
        # that fall inside it.
        framed = {}
        for span in entry["ranges"]:
            fit = [n for n in cards if n["start"] <= span["start"] and span["end"] <= n["end"]]
            if not fit:
                raise ValueError(f"{where}: lines {span['start']}-{span['end']} are outside "
                                 f"{sorted({(n['start'], n['end']) for n in cards})} (stale line numbers?)")
            actual = fit[0]["src"].split("\n")[span["start"] - fit[0]["start"]].strip()
            if "text" in span and actual != str(span["text"]).strip():
                raise ValueError(f"{where}: line {span['start']} is {actual!r}, expected {span['text']!r}")
            for n in fit:
                framed.setdefault(id(n), (n, []))[1].append(span)
        for n, spans in framed.values():
            n["innovation"] = {"role": entry["role"], "ranges": spans,
                               **{k: entry[k] for k in ("summary", "provenance") if k in entry}}
        marked.add(key)
    payload["innovation"] = {k: spec[k] for k in ("label", "definition", "review") if k in spec}
    payload["innovation"].update(functions=len(marked), unmatched=unmatched,
                                 cards=sum(1 for n in nodes if n.get("innovation")))
    if spec.get("important_label"):
        payload["important_label"] = spec["important_label"]
    return payload


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
    boundary_exclusions = []
    if insts:
        # samples are recorded per function; each carries the instance it came from
        by_inst = {}
        for c in cg["calls"]:
            for smp in (c.get("samples") or []):
                if "inst" in smp:
                    by_inst.setdefault(smp["inst"], []).append(_normalize_sample_outcome(smp))

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
            run_ex = sorted(x for x in cv.get("executed_lines", []) if st <= x <= en)
            run_mi = sorted(x for x in cv.get("missing_lines", []) if st <= x <= en)
            context_coverage = "executed_lines" in m
            ex = sorted(x for x in m["executed_lines"] if st <= x <= en) if context_coverage else run_ex
            mi = sorted((set(run_ex) | set(run_mi)) - set(ex)) if context_coverage else run_mi
            exs = set(ex)
            if context_coverage:
                observed_arcs = {tuple(arc) for arc in m.get("executed_arcs", [])}
                possible_arcs = (cv.get("executed_branches") or []) + (cv.get("missing_branches") or [])
                part = sorted({arc[0] for arc in possible_arcs if arc and arc[0] in exs and tuple(arc) not in observed_arcs})
            else:
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
                "coverage_scope": ("merged_call_sites" if m["parent"] == -2 else "call_site_group") if context_coverage else "whole_run",
                "call_scope": "merged_call_sites" if m["parent"] == -2 else "call_site_group",
                "raw_instance": idx, "run_ex": run_ex,
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

        if "instance_edges" in cg:
            # New captures preserve the actual parent even when a hot callee is
            # merged. Never project function-level edges onto sibling cards.
            for record in sorted(cg["instance_edges"], key=lambda e: e["seq"]):
                c = inst_node.get(record["parent"])
                n = inst_node.get(record["to"])
                if c is None or n is None:
                    continue
                cline = record["cline"]
                edges.append({"from": c, "line": cline, "to": n,
                              "n": record["count"], "seq": record["seq"],
                              "via": pretty_via(record.get("via", "")),
                              "provenance": "instance_edge"})
                if n not in first_caller and c != n:
                    walk, seen = c, set()
                    while walk not in seen and walk != n and walk in first_caller:
                        seen.add(walk)
                        walk = first_caller[walk][0]
                    if walk != n:
                        first_caller[n] = (c, cline, record["seq"])
            for idx, m in enumerate(insts):
                if m["parent"] != -1 or idx not in inst_node:
                    continue
                origin = thread_parent(idx)
                if origin is None:
                    continue
                c, cline = inst_node[origin[0]], origin[1]
                n = inst_node[idx]
                edges.append({"from": c, "line": cline, "to": n, "n": m["count"],
                              "seq": m["seq"], "via": "thread", "provenance": "thread_origin"})
                if n not in first_caller and c != n:
                    first_caller[n] = (c, cline, m["seq"])
        else:
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
        # External/native endpoints are measured calls, with source as reference
        # only. They are attached before reachability and layout so every visible
        # caller can open its actual observed destination.
        for boundary_index, record in enumerate(cg.get("external_calls") or []):
            c = inst_node.get(record["parent"])
            boundary_id = record.get("id", boundary_index)
            if c is None or c not in nodes:
                boundary_exclusions.append({"id": boundary_id, "reason": "project caller has no rendered source card"})
                continue
            cline = record["cline"]
            if not nodes[c]["start"] <= cline <= nodes[c]["end"]:
                boundary_exclusions.append({"id": boundary_id, "reason": "recorded call line is outside caller source", "line": cline})
                continue
            target = record["target"]
            outcomes, outcomes_provenance = _boundary_outcomes(record, cg.get("external_capture") or {})
            source = target.get("source") or ""
            source_available = bool(source)
            if not source_available:
                source = "\n".join([
                    "# Observed " + target.get("kind", "external") + " call boundary",
                    "# Target: " + target.get("module", "") + "." + target.get("name", "unknown"),
                    "# Python source is unavailable; internal execution was not traced.",
                    "# Open the recorded values to inspect available arguments and outcomes.",
                ])
            lines = source.rstrip("\n").split("\n")
            st = max(1, target.get("first") or 1) if source_available else 1
            n = max(nodes, default=-1) + 1
            maxlen = max((len(line) for line in lines), default=0)
            nodes[n] = {
                "id": n, "file": target.get("file") or "<" + target.get("kind", "external") + ">",
                "name": target.get("name") or "observed external call",
                "start": st, "def": st, "end": st + len(lines) - 1,
                "src": "\n".join(lines), "nlines": len(lines),
                "ex": [], "mi": [], "partial": [], "run_ex": [],
                "coverage_scope": "boundary_only", "call_scope": "call_site_group",
                "calls": record["count"], "seq": record.get("seq", 0),
                "samples": [_normalize_sample_outcome(s) for s in record.get("samples") or []], "important": False,
                "w": max(MIN_W, min(MAX_W, round(GUT + maxlen * CHW + 26))),
                "h": HDR + len(lines) * LH + RET,
                "boundary": {"id": boundary_id, "parent_instance": record["parent"],
                             "kind": target.get("kind", "external"), "target": target,
                             "expression": record.get("expression", ""),
                             "expression_exact": record.get("expression_exact", False),
                             "expression_note": record.get("expression_note", ""),
                             "outcomes": outcomes,
                             "outcomes_provenance": outcomes_provenance,
                             "outcomes_note": outcomes_provenance["note"] if outcomes_provenance else "",
                             "contexts": record.get("contexts") or [],
                             "source_reference_only": source_available},
            }
            edges.append({"from": c, "line": cline, "to": n, "n": record["count"],
                          "seq": record.get("seq", 0), "via": "", "boundary": True,
                          "boundary_id": boundary_id, "expression": record.get("expression", ""),
                          "expression_exact": record.get("expression_exact", False),
                          "provenance": "external_call"})
            first_caller[n] = (c, cline, record.get("seq", 0))
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
                "coverage_scope": "whole_run", "call_scope": "function",
                "calls": c["count"], "seq": c["seq"],
                "w": max(MIN_W, min(MAX_W, round(GUT + maxlen * CHW + 26))),
                "h": HDR + len(lines) * LH + RET,
                "samples": [_normalize_sample_outcome(s) for s in c.get("samples") or []],
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
    context_coverage = any(n["coverage_scope"] in ("call_site_group", "merged_call_sites") for n in nodes.values())
    drawn_boundary_ids = {n["boundary"]["id"] for n in nodes.values() if n.get("boundary")}
    excluded_ids = {record["id"] for record in boundary_exclusions}
    for index, record in enumerate(cg.get("external_calls") or []):
        boundary_id = record.get("id", index)
        if boundary_id not in drawn_boundary_ids and boundary_id not in excluded_ids:
            boundary_exclusions.append({"id": boundary_id, "reason": "caller is outside the selected entry's reachable tree"})
    return {
        "title": title,
        "brand": brand,
        "command": command,
        "outcome": outcome,
        "coverage_scope": "call_site_group" if context_coverage else "whole_run",
        "coverage_note": (
            "Line colors show lines recorded in this card's caller context, grouped across its repeated calls. "
            "Merged helpers are explicitly labeled. Other-call-site links open the context where a line ran. "
            "External and native cards prove the observed call boundary; their reference source has no internal line coverage."
        ) if context_coverage else (
            "Line coverage combines every invocation in the recorded command. "
            "A call-site card groups repeated calls from one calling context, not one invocation. "
            "Its call arrows describe that context; lines with calls observed only on other "
            "call-site cards link to those cards. Per-invocation line coverage was not recorded."
        ),
        "entry_label": f"{entry_name} — where this run starts",
        "geom": {"LH": LH, "HDR": HDR, "ncols": ncols,
                 "world_w": col_x[-1] + col_w[-1], "world_h": max(col_bottom)},
        "totals": {
            "functions": len(nodes),
            "edges": len(edges),
            "calls": sum(n["calls"] for n in nodes.values()),
            "lines": sum(n["nlines"] for n in nodes.values() if not n.get("boundary")),
            "reference_lines": sum(n["nlines"] for n in nodes.values() if n.get("boundary")),
            "executed": sum(len(n["ex"]) for n in nodes.values()),
            "columns": ncols,
            "dropped": dropped,
            "important": sum(1 for n in nodes.values() if n["important"]),
            "sampled": sum(1 for n in nodes.values() if n["samples"]),
            "boundaries": len(drawn_boundary_ids),
        },
        "boundary_audit": {"recorded": len(cg.get("external_calls") or []),
                           "rendered": len(drawn_boundary_ids), "excluded": boundary_exclusions},
        "external_capture": cg.get("external_capture"),
        "main": entry_id,
        "nodes": [nodes[i] for i in sorted(nodes)],
        "edges": edges,
        "workflow": _workflow_from_important(important, nodes),
    }
