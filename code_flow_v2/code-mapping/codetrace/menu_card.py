#!/usr/bin/env python3
"""Hand a finished call-tree.html to the Code Mapping Sessions menu.

    python menu_card.py --out <codetrace out dir> --slug perturb_flow --name perturb_flow \
        --tag "training · libero_spatial" --what "What the traced run does." --fam gap [--copy]

Reads payload_call_tree.json (+ run.json) from --out and prints, filled from the
trace's own numbers: the <a class="run"> card for index.html, the README table
row, and the menu's new totals strip.  With --copy it also places the page at
<menu>/projects/<slug>/<page> with a real <title>.  See ../../PUBLISHING.md.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

MENU = "/mnt/sata1/andres/menuCodeMapping"
FAMS = ("gap", "cap", "rldx", "data")
TOTALS = ("Sessions", "Functions traced", "Calls recorded", "Lines executed", "Lines in scope")


def fmt(n: int) -> str:
    return f"{n:,}"


def default_menu():
    # Prefer the checkout containing this pack, wherever it was cloned.
    for parent in Path(__file__).resolve().parents:
        if ((parent / "index.html").is_file()
                and (parent / "projects").is_dir()
                and (parent / "code_flow_v2" / "PUBLISHING.md").is_file()):
            return str(parent)
    # Preserve the standalone working pack's existing destination on linux3.
    legacy = Path(MENU)
    if (legacy / "index.html").is_file() and (legacy / "projects").is_dir():
        return str(legacy)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="codetrace output dir: call-tree.html + payload_call_tree.json")
    ap.add_argument("--slug", required=True, help="folder under projects/, e.g. perturb_flow")
    ap.add_argument("--name", required=True, help="card title")
    ap.add_argument("--title", default=None,
                    help="the page's <title> (browser tab); default '<name>'. For a pair use e.g. 'perturb_flow · Training'")
    ap.add_argument("--tag", default="", help="grey text after the name, e.g. 'training · libero_spatial'")
    ap.add_argument("--what", required=True, help="one or two sentences: what the traced run does")
    ap.add_argument("--fam", choices=FAMS, default="gap", help="stripe colour family")
    ap.add_argument("--result", default="", help="appended to the verdict, e.g. '9/12 picked'")
    ap.add_argument("--page", default="index.html", help="file name under projects/<slug>/")
    ap.add_argument("--menu", default=default_menu(),
                    help="menu checkout (default: containing codeMapping clone, then existing linux3 checkout)")
    ap.add_argument("--copy", action="store_true", help="copy the page into the menu now")
    ap.add_argument("--force", action="store_true", help="overwrite an existing page")
    a = ap.parse_args()
    if a.copy and not a.menu:
        ap.error("--copy needs --menu /path/to/menuCodeMapping when the menu checkout cannot be located")

    out = Path(a.out)
    src = out / "call-tree.html"
    payload = out / "payload_call_tree.json"
    if not src.exists() or not payload.exists():
        print(f"menu_card: {out} needs call-tree.html and payload_call_tree.json (run codetrace first)", file=sys.stderr)
        return 2
    P = json.loads(payload.read_text(encoding="utf-8"))
    t = P["totals"]
    entry = next(n for n in P["nodes"] if n["id"] == P["main"])
    command = P.get("command", "")
    # cards carry no absolute paths: "/home/x/envs/y/bin/python3.10 train.py" -> "python train.py"
    command = re.sub(r"^\S*/python[\d.]*(?=\s|$)", "python", command)
    outcome = P.get("outcome", "")
    if a.result:
        outcome += " · " + a.result
    size = src.stat().st_size
    size_s = f"{size / 1e6:.1f} MB" if size >= 1e6 else f"{size / 1e3:.0f} KB"
    pct = 100.0 * t["executed"] / max(t["lines"], 1)
    rel = f"projects/{a.slug}/{a.page}"
    E = html.escape

    card = f"""        <a class="run" style="--fam: var(--fam-{a.fam})"
           href="{rel}">
          <div>
            <h3 class="title"><span class="name">{E(a.name)}</span> <span class="slug">{E(a.tag)}</span></h3>
            <p class="what">{E(a.what)}</p>
            <code class="cmd">{E(command)}</code>
            <p class="local">{rel}<span class="sep">/</span>{size_s}<span class="sep">/</span>entry <code>{E(entry["name"])}</code> &middot; {E(entry["file"])}</p>
          </div>
          <div class="metrics">
            <span class="verdict">{E(outcome)}</span>
            <div class="cov">
              <div class="covtop"><span class="covlabel">Line coverage</span><span><b>{pct:.1f}%</b> &middot; {fmt(t["executed"])}/{fmt(t["lines"])}</span></div>
              <div class="bar"><i style="width: {pct:.1f}%"></i></div>
            </div>
            <dl class="counts">
              <div><dt>Functions</dt><dd>{fmt(t["functions"])}</dd></div>
              <div><dt>Edges</dt><dd>{fmt(t["edges"])}</dd></div>
              <div><dt>Calls</dt><dd>{fmt(t["calls"])}</dd></div>
            </dl>
          </div>
        </a>"""

    row = (f"| {a.name}{(' · ' + a.tag) if a.tag else ''} | `{command}` | {outcome} | "
           f"{fmt(t['executed'])} / {fmt(t['lines'])} lines | [local]({rel}) |")

    print("=== card — paste into index.html, inside the shelf's <div class=\"runs\">\n")
    print(card)
    print("\n=== row — append to README.md's Sessions table\n")
    print(row)

    index = Path(a.menu) / "index.html" if a.menu else None
    if index is not None and index.exists():
        cur = dict(re.findall(r'<div class="tot"><b>([\d,]+)</b><span>([^<]+)</span></div>', index.read_text(encoding="utf-8")))
        cur = {label: int(v.replace(",", "")) for v, label in cur.items()}
        add = dict(zip(TOTALS, (1, t["functions"], t["calls"], t["executed"], t["lines"])))
        print("\n=== totals strip — replace the five values at the top of index.html\n")
        for label in TOTALS:
            if label in cur:
                print(f'      <div class="tot"><b>{fmt(cur[label] + add[label])}</b><span>{label}</span></div>')
        print("\n(and add 1 to the shelf's <span class=\"n\">…</span> count)")

    if a.copy:
        dst = Path(a.menu) / "projects" / a.slug / a.page
        if dst.exists() and not a.force:
            print(f"\nmenu_card: {dst} exists — pass --force to overwrite", file=sys.stderr)
            return 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        page = src.read_text(encoding="utf-8")
        title = a.title or a.name
        page = page.replace("<title>Code trace</title>", f"<title>{E(title)}</title>", 1)
        # the viewer sets document.title from the payload at load, which would undo the
        # static <title>; rename it in the payload too (its "title" is the first key)
        page = re.sub(r'(<script id="payload" type="application/json">\{"title":)"(?:[^"\\]|\\.)*"',
                      lambda m: m.group(1) + json.dumps(title), page, count=1)
        dst.write_text(page, encoding="utf-8")
        shutil.copymode(src, dst)
        print(f"\ncopied → {dst}  ({size_s})")
    elif a.menu:
        print(f"\n(page not copied; add --copy to place it at {Path(a.menu) / 'projects' / a.slug / a.page})")
    else:
        print("\n(page not copied; pass --menu /path/to/menuCodeMapping --copy to choose its destination)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
