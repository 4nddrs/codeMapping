#!/usr/bin/env python3
"""Check a rendered call-tree page in a headless browser: values, shapes, errors.

    python check_values.py PAGE --card TEXT [--lines A-B] [--popup LINE ...]
                           [--expect FILE] [--shot PNG] [--json]

PAGE is a call-tree.html path or URL (the served page, not the template).
--card TEXT     text typed into the page's search box; the first match is the card
--lines A-B     print the shape hints shown after lines A..B of that card
--popup LINE    right-click LINE (a real contextmenu gesture) and print the value
                popup: groups, rows, and the expanded first row; repeatable
--expect FILE   JSON list of checks, see below; the exit code is 1 when one fails
--shot PNG      screenshot after the last popup
--json          machine-readable output

An expectation file is a list of objects:
  {"card": "x = self.drop(cond_embeddings + position_embeddings)",
   "hints": {"473": "x (8, 513, 256)", "493": "x (8, 6, 2)"},
   "popup": 473,
   "rows": ["x = (8, 513, 256)", "cond_embeddings = (8, 513, 256)"],
   "not_rows": ["(at function exit)"]}
`hints` values are exact texts ("" for no hint); `rows` are substrings that must
appear in some popup row, `not_rows` substrings that must appear in none.
Every check also fails on a JavaScript error, a card that is not found, or a
line that is not visible. Needs Google Chrome or Chromium on PATH (or
$CHROME); no other dependency. Use it on localhost and on the deployed page.
"""
import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request


class WS:
    """Minimal RFC 6455 client for Chrome's local DevTools endpoint."""

    def __init__(self, url):
        _, rest = url.split("://", 1)
        host, path = rest.split("/", 1)
        hostname, port = host.split(":")
        self.sock = socket.create_connection((hostname, int(port)), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        if b" 101 " not in buf.split(b"\r\n", 1)[0]:
            raise RuntimeError("websocket handshake failed: " + buf[:120].decode(errors="replace"))
        self.rest = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.rest) < n:
            chunk = self.sock.recv(max(65536, n - len(self.rest)))
            if not chunk:
                raise ConnectionError("websocket closed")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        if len(data) < 126:
            head.append(0x80 | len(data))
        elif len(data) < 65536:
            head.append(0x80 | 126); head += struct.pack(">H", len(data))
        else:
            head.append(0x80 | 127); head += struct.pack(">Q", len(data))
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        message = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            if b1 & 0x80:
                self._read(4)
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 8:
                raise ConnectionError("websocket closed")
            if op in (9, 10):
                continue
            message += payload
            if b0 & 0x80:
                return message.decode()

    def close(self):
        self.sock.close()


class Page:
    def __init__(self, url, width=1600, height=1000):
        chrome = os.environ.get("CHROME") or next((c for c in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(c)), None)
        if not chrome:
            sys.exit("check_values: no Chrome/Chromium on PATH (set $CHROME)")
        s = socket.socket(); s.bind(("127.0.0.1", 0)); self.port = s.getsockname()[1]; s.close()
        self.profile = tempfile.mkdtemp(prefix="check-values-")
        self.proc = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                                      f"--remote-debugging-port={self.port}", "--remote-allow-origins=*",
                                      f"--user-data-dir={self.profile}", f"--window-size={width},{height}", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        targets = None
        for _ in range(200):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json")); break
            except Exception:
                time.sleep(0.1)
        if not targets:
            self.close(); sys.exit("check_values: Chrome did not start")
        self.ws = WS(next(t for t in targets if t["type"] == "page")["webSocketDebuggerUrl"])
        self.next_id, self.events = 0, []
        for domain in ("Page", "Runtime", "Log"):
            self.call(domain + ".enable")
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        self.call("Page.navigate", url=url)
        start = time.time()
        while time.time() - start < 120 and self.js("document.readyState") != "complete":
            time.sleep(0.3)
        time.sleep(2.5)

    def call(self, method, **params):
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.next_id:
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"]))
                return msg.get("result", {})
            self.events.append(msg)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:800])
        return r["result"].get("value")

    def errors(self):
        out = []
        for e in self.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                out.append(json.dumps(e["params"].get("exceptionDetails", {}).get("exception", {}).get("description", e["params"]))[:300])
            elif m == "Log.entryAdded" and e["params"]["entry"]["level"] == "error" and "favicon" not in e["params"]["entry"].get("url", ""):
                out.append(e["params"]["entry"].get("text", "")[:300])
            elif m == "Runtime.consoleAPICalled" and e["params"]["type"] == "error":
                out.append(json.dumps([a.get("value") for a in e["params"].get("args", [])])[:300])
        return out

    def screenshot(self, path):
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


FIND_CARD = """(async (text) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  const q = document.getElementById('q'); q.focus(); q.value = text;
  q.dispatchEvent(new Event('input', {bubbles: true})); await wait(700);
  q.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true})); await wait(2500); q.blur();
  const vis = r => { const b = r.getBoundingClientRect(); return b.width && b.top > 0 && b.bottom < innerHeight; };
  const row = [...document.querySelectorAll('.row')].filter(vis)[0];
  if (!row) return null;
  const panel = row.closest('.panel');
  return {name: panel && panel.querySelector('.phdr .fn') ? panel.querySelector('.phdr .fn').textContent : '',
          loc: panel && panel.querySelector('.phdr .loc') ? panel.querySelector('.phdr .loc').textContent : ''};
})"""

HINTS = """((a, b) => {
  const vis = r => { const bb = r.getBoundingClientRect(); return bb.width && bb.top > 0 && bb.bottom < innerHeight; };
  const out = {};
  for (let l = a; l <= b; l++) {
    const row = [...document.querySelectorAll('.row[data-l="' + l + '"]')].filter(vis)[0];
    if (row) out[l] = [row.querySelector('.src').textContent.trim(), (row.querySelector('.shint') || {textContent: ''}).textContent];
  }
  return out;
})"""

POPUP = """(async (line) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); await wait(150);
  const vis = r => { const b = r.getBoundingClientRect(); return b.width && b.top > 0 && b.bottom < innerHeight; };
  const row = [...document.querySelectorAll('.row[data-l="' + line + '"]')].filter(vis)[0];
  if (!row) return {error: 'line ' + line + ' is not visible on the current card'};
  const b = row.getBoundingClientRect(), x = b.left + Math.min(120, b.width / 2), y = b.top + b.height / 2;
  const opts = {bubbles: true, cancelable: true, clientX: x, clientY: y, button: 2, buttons: 2};
  row.dispatchEvent(new PointerEvent('pointerdown', opts));
  row.dispatchEvent(new MouseEvent('mousedown', opts));
  row.dispatchEvent(new MouseEvent('contextmenu', opts));
  row.dispatchEvent(new PointerEvent('pointerup', opts));
  row.dispatchEvent(new MouseEvent('mouseup', opts));
  await wait(400);
  const vals = document.getElementById('vals');
  if (!vals || vals.style.display === 'none') return {error: 'the value popup did not open on line ' + line};
  const rows = [...vals.querySelectorAll(':scope > .vr, :scope > details > summary, :scope > .empty')].map(e => e.textContent.trim().replace(/^▸/, ''));
  const first = vals.querySelector(':scope > details > summary');
  let expanded = null;
  if (first) { first.click(); await wait(250); expanded = first.parentElement.innerText.trim(); }
  return {header: (vals.querySelector('.vh span') || {}).textContent || '',
          groups: [...vals.querySelectorAll('.sec')].map(e => e.textContent.trim()), rows, expanded};
})"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("page")
    ap.add_argument("--card", help="search text that finds the card")
    ap.add_argument("--lines", help="A-B: print shape hints on these lines")
    ap.add_argument("--popup", type=int, action="append", default=[], help="right-click this line and print the popup")
    ap.add_argument("--expect", help="JSON file with checks")
    ap.add_argument("--shot", help="screenshot path (png)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    url = args.page if "://" in args.page else "file://" + os.path.abspath(args.page)
    checks = json.load(open(args.expect)) if args.expect else []
    if args.card or args.lines or args.popup:
        c = {"card": args.card}
        if args.lines:
            a, b = args.lines.split("-")
            c["lines"] = [int(a), int(b)]
        c["popups"] = args.popup
        checks.insert(0, c)
    if not checks:
        ap.error("give --card with --lines/--popup, or --expect FILE")

    page, failures, report = Page(url), [], []
    try:
        for c in checks:
            entry = {"card": c.get("card")}
            found = page.js(f"({FIND_CARD})({json.dumps(c.get('card') or '')})") if c.get("card") else {"name": "(current view)"}
            if not found:
                failures.append(f"card not found for search {c.get('card')!r}")
                report.append(dict(entry, error="card not found")); continue
            entry["found"] = found
            hints_wanted = c.get("hints") or {}
            lines = c.get("lines") or (hints_wanted and [min(map(int, hints_wanted)), max(map(int, hints_wanted))])
            if lines:
                hints = page.js(f"({HINTS})({lines[0]}, {lines[1]})")
                entry["hints"] = hints
                for ln, want in hints_wanted.items():
                    got = hints.get(str(ln))
                    if got is None:
                        failures.append(f"{c.get('card')!r}: line {ln} is not visible")
                    elif got[1] != want:
                        failures.append(f"{c.get('card')!r}: line {ln} hint {got[1]!r}, expected {want!r}")
            popups = list(c.get("popups") or []) + ([c["popup"]] if c.get("popup") is not None else [])
            entry["popups"] = {}
            for ln in popups:
                res = page.js(f"({POPUP})({ln})")
                entry["popups"][ln] = res
                if res.get("error"):
                    failures.append(f"{c.get('card')!r}: {res['error']}"); continue
                rows = res["rows"]
                if c.get("popup") == ln:
                    for want in c.get("rows") or []:
                        if not any(want in r for r in rows):
                            failures.append(f"{c.get('card')!r} line {ln}: no row contains {want!r}; rows: {rows}")
                    for bad in c.get("not_rows") or []:
                        if any(bad in r for r in rows):
                            failures.append(f"{c.get('card')!r} line {ln}: a row contains {bad!r}; rows: {rows}")
            report.append(entry)
        if args.shot:
            page.screenshot(args.shot)
        errors = page.errors()
        for e in errors:
            failures.append("JavaScript error: " + e)
    finally:
        page.close()

    if args.json:
        print(json.dumps({"page": url, "checks": report, "js_errors": errors, "failures": failures}, ensure_ascii=False, indent=1))
    else:
        for entry in report:
            print(f"== card {entry.get('found', {}).get('name', '?')}  {entry.get('found', {}).get('loc', '')}  (search {entry.get('card')!r})")
            for ln, (src, hint) in sorted((entry.get("hints") or {}).items(), key=lambda kv: int(kv[0])):
                print(f"  {ln:>5}  {src[:70]:<70}  {hint}")
            for ln, res in (entry.get("popups") or {}).items():
                print(f"  popup line {ln}: {res.get('error') or res['header']}")
                for r in res.get("rows") or []:
                    print(f"      {r}")
        print(f"js_errors: {len(errors)}")
        print("FAIL" if failures else "OK", *("\n  - " + f for f in failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
