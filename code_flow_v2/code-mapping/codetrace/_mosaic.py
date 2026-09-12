"""Turn coverage into the file-mosaic payload: every source file, full text."""
from __future__ import annotations

from pathlib import Path

LH, HDR = 17, 46
MAXL = 120          # lines per sub-column, so tall files read as blocks not slivers
CHW, GUT = 7.31, 67
COLD_W, COLD_H = 330, 92
GAP = 44


def build(*, root: Path, roots, cov, command, outcome, title, brand):
    cov_files = {}
    for k, v in (cov.get("files") or {}).items():
        kp = Path(k)
        try:
            rel = kp.resolve().relative_to(root).as_posix() if kp.is_absolute() else kp.as_posix()
        except ValueError:
            continue
        cov_files[rel] = v

    # every .py under the watched roots, imported or not
    allfiles = []
    for r in roots:
        p = root / r
        if p.is_file() and p.suffix == ".py":
            allfiles.append(p.relative_to(root).as_posix())
        elif p.is_dir():
            for q in sorted(p.rglob("*.py")):
                if "__pycache__" not in q.parts:
                    allfiles.append(q.relative_to(root).as_posix())

    files = []
    for rel in allfiles:
        try:
            src = (root / rel).read_text(errors="replace")
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
