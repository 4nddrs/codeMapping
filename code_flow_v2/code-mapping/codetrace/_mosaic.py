"""Turn coverage into the file-mosaic payload: every source file, full text."""
from __future__ import annotations

from pathlib import Path

LH, HDR = 17, 46
MAXL = 120          # lines per sub-column, so tall files read as blocks not slivers
CHW, GUT = 7.31, 67
COLD_W, COLD_H = 330, 92
GAP = 44


def build(*, root: Path, roots, cov, command, outcome, title, brand, trace_packages=None):
    # --trace-package roots may live outside the repo; they are keyed NAME/<rel>
    # like the call tree does, instead of failing relative_to(root).
    trace_packages = {k: Path(v) for k, v in (trace_packages or {}).items()}

    def key_for(path: Path):
        for name, location in trace_packages.items():
            try:
                inside = path.relative_to(location)
            except ValueError:
                continue
            return name if str(inside) == "." else name + "/" + inside.as_posix()
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return None

    def resolve(rel: str) -> Path:
        for name, location in trace_packages.items():
            if rel == name:
                return location
            if rel.startswith(name + "/"):
                return location / rel[len(name) + 1:]
        return root / rel

    cov_files = {}
    for k, v in (cov.get("files") or {}).items():
        kp = Path(k)
        rel = key_for(kp.resolve() if kp.is_absolute() else (root / kp).resolve())
        if rel is None:
            continue
        cov_files[rel] = v

    # every .py under the watched roots, imported or not
    allfiles = []
    for r in roots:
        p = root / r
        if p.is_file() and p.suffix == ".py":
            rel = key_for(p)
            if rel is not None:
                allfiles.append(rel)
        elif p.is_dir():
            for q in sorted(p.rglob("*.py")):
                if "__pycache__" in q.parts:
                    continue
                rel = key_for(q)
                if rel is not None:
                    allfiles.append(rel)

    files = []
    for rel in allfiles:
        try:
            src = resolve(rel).read_text(errors="replace")
        except OSError:
            continue
        lines = src.split("\n")
        c = cov_files.get(rel)
        if c:
            ex = sorted(c.get("executed_lines", []))
            mi = sorted(c.get("missing_lines", []))
            exs = set(ex)
            part = sorted({b[0] for b in (c.get("missing_branches") or []) if b and b[0] in exs})
            nstmt = (c.get("summary") or {}).get("num_statements", 0)
            loaded = True
        else:
            ex, mi, part, nstmt, loaded = [], [], [], 0, False
        maxlen = max((len(l) for l in lines), default=0)
        files.append({
            "path": rel, "src": src, "nlines": len(lines),
            "ex": ex, "mi": mi, "partial": part, "loaded": loaded, "nstmt": nstmt,
            "maxlen": maxlen,
        })

    files.sort(key=lambda f: (0 if f["loaded"] else 1, -len(f["ex"]), f["path"]))

    # ---------- layout: executed files as blocks, the rest as compact tiles ----------
    panels = []
    for f in files:
        if not f["loaded"]:
            panels.append({"f": f, "cold": True, "colW": COLD_W, "ncols": 1, "rows": 0,
                           "w": COLD_W, "h": COLD_H})
            continue
        colW = max(340, min(1000, round(GUT + f["maxlen"] * CHW + 26)))
        ncols = max(1, -(-f["nlines"] // MAXL))
        rows = min(f["nlines"], MAXL)
        panels.append({"f": f, "cold": False, "colW": colW, "ncols": ncols, "rows": rows,
                       "w": colW * ncols, "h": HDR + rows * LH})

    hot = [p for p in panels if not p["cold"]]
    cold = [p for p in panels if p["cold"]]
    area = sum(p["w"] * p["h"] for p in hot) or 1
    target_w = (area * 1.7) ** 0.5
    cx = cy = row_h = 0
    for p in hot:
        if cx > 0 and cx + p["w"] > target_w:
            cx = 0
            cy += row_h + GAP
            row_h = 0
        p["x"], p["y"] = cx, cy
        cx += p["w"] + GAP
        row_h = max(row_h, p["h"])
    cold_top = cy + row_h + GAP * 2.4
    per_row = max(1, int(target_w // (COLD_W + GAP)))
    for i, p in enumerate(cold):
        p["x"] = (i % per_row) * (COLD_W + GAP)
        p["y"] = cold_top + 40 + (i // per_row) * (COLD_H + GAP)

    out_files = []
    for p in panels:
        f = dict(p["f"])
        f.update(x=p["x"], y=p["y"], w=p["w"], h=p["h"],
                 colW=p["colW"], ncols=p["ncols"], rows=p["rows"], cold=p["cold"])
        out_files.append(f)

    return {
        "title": title,
        "brand": brand,
        "command": command,
        "outcome": outcome,
        "geom": {"LH": LH, "HDR": HDR, "MAXL": MAXL, "COLD_H": COLD_H,
                 "cold_top": cold_top,
                 "world_w": max((p["x"] + p["w"] for p in panels), default=0),
                 "world_h": max((p["y"] + p["h"] for p in panels), default=0)},
        "totals": {
            "files": len(files),
            "files_loaded": sum(1 for f in files if f["loaded"]),
            "lines": sum(f["nlines"] for f in files),
            "statements": sum(f["nstmt"] for f in files),
            "executed": sum(len(f["ex"]) for f in files),
            "cold": len(cold),
            "cold_lines": sum(p["f"]["nlines"] for p in cold),
        },
        "files": out_files,
    }
