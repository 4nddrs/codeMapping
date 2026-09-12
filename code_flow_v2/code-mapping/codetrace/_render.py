"""Inline a payload into a viewer template -> one standalone HTML file."""
from __future__ import annotations

import json
import math
from pathlib import Path


def _finite(o):
    """JSON has no NaN/Infinity: json.dumps writes bare `NaN`/`Infinity` tokens, JSON.parse rejects
    them and the page renders blank. A captured value holding inf/nan (a tensor head, a float local)
    is enough to trigger it, so write non-finite floats as the strings the popup should show."""
    if isinstance(o, float) and not math.isfinite(o):
        return "nan" if o != o else ("inf" if o > 0 else "-inf")
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def render(template: Path, payload, out: Path) -> Path:
    data = json.dumps(_finite(payload), separators=(",", ":"), allow_nan=False)
    # keep any source text from closing the <script> block it lives in
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # check the TEMPLATE, not the result: traced source that itself contains the
    # string __PAYLOAD__ (e.g. a viewer builder) would otherwise abort the render
    template_html = Path(template).read_text(encoding="utf-8")
    if "__PAYLOAD__" not in template_html:
        raise SystemExit(f"codetrace: {template} has no __PAYLOAD__ placeholder")
    html = template_html.replace("__PAYLOAD__", data)
    out.write_text(html, encoding="utf-8")
    return out
