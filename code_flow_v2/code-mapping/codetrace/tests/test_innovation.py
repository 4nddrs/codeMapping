#!/usr/bin/env python3
"""Innovation-frame regressions on a payload built from a real traced execution.

Run this file directly or use unittest discovery from the tests directory.
Requires coverage, like test_context_lines.py; no project datasets or GPU.
"""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import _calltree
import _render
import test_context_lines as _capture_fixture


class InnovationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = _capture_fixture.ContextLineTests(methodName="test_distinct_returns_and_sample_lines_remain_separate")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        graph, lines, arcs, _ = self.fixture.run_capture()
        coverage = {"files": {"fixture.py": {
            "executed_lines": sorted(lines),
            "executed_branches": [list(arc) for arc in sorted(arcs) if min(arc) > 0],
            "missing_lines": [], "missing_branches": [],
        }}}
        self.payload = _calltree.build(
            root=self.fixture.root, cg=graph, cov=coverage, command="python fixture.py",
            outcome="fixture passed", title="Innovation regression", brand="Tests", entry="main")
        self.node = next(n for n in self.payload["nodes"]
                         if not n.get("boundary") and n["name"] != "main" and n["end"] > n["def"])
        self.line = self.node["def"] + 1
        self.text = self.node["src"].split("\n")[self.line - self.node["start"]].strip()

    def spec(self, **range_overrides):
        span = {"start": self.line, "end": self.line, "what": "the reviewed line", "text": self.text}
        span.update(range_overrides)
        return {"label": "Fixture innovation", "important_label": "★ curated stage",
                "functions": [
                    {"file": self.node["file"], "function": self.node["name"], "role": "core",
                     "summary": "fixture summary", "ranges": [span]},
                    {"file": "fixture.py", "function": "never_called", "role": "supporting",
                     "ranges": [{"start": 1, "end": 1, "what": "not rendered"}]},
                ]}

    def cards(self):
        return [n for n in self.payload["nodes"]
                if (n["file"], n["name"]) == (self.node["file"], self.node["name"]) and not n.get("boundary")]

    def test_build_alone_adds_no_innovation_fields(self):
        self.assertNotIn("innovation", self.payload)
        self.assertNotIn("important_label", self.payload)
        self.assertFalse(any("innovation" in n for n in self.payload["nodes"]))

    def test_every_card_of_the_function_is_marked_and_missing_functions_reported(self):
        _calltree.apply_innovation(self.payload, self.spec())
        marked = [n for n in self.payload["nodes"] if n.get("innovation")]
        self.assertEqual(marked, self.cards())
        self.assertEqual(marked[0]["innovation"]["role"], "core")
        self.assertEqual(marked[0]["innovation"]["ranges"][0]["start"], self.line)
        summary = self.payload["innovation"]
        self.assertEqual((summary["functions"], summary["cards"]), (1, len(marked)))
        self.assertEqual(summary["unmatched"], ["fixture.py:never_called"])
        self.assertEqual(summary["label"], "Fixture innovation")
        self.assertEqual(self.payload["important_label"], "★ curated stage")

    def test_only_cards_whose_lines_contain_the_ranges_are_framed(self):
        other = copy.deepcopy(self.node)          # same qualified name, different source span
        other.update(id=max(n["id"] for n in self.payload["nodes"]) + 1,
                     start=self.node["end"] + 10, def_=None, end=self.node["end"] + 20)
        self.payload["nodes"].append(other)
        _calltree.apply_innovation(self.payload, self.spec())
        self.assertNotIn("innovation", other)
        self.assertTrue(all("innovation" in n for n in self.cards() if n is not other))

    def test_same_named_cards_with_different_source_each_get_their_own_range(self):
        other = copy.deepcopy(self.node)          # e.g. a property setter next to its getter
        other.update(id=max(n["id"] for n in self.payload["nodes"]) + 1,
                     start=self.node["end"] + 10, end=self.node["end"] + 12,
                     src="\n".join(["def setter(self, v):", "    self._v = v", "    return v"]))
        self.payload["nodes"].append(other)
        spec = self.spec()
        spec["functions"][0]["ranges"].append({"start": other["start"] + 1, "end": other["start"] + 1,
                                               "what": "setter body", "text": "self._v = v"})
        _calltree.apply_innovation(self.payload, spec)
        self.assertEqual([r["start"] for r in other["innovation"]["ranges"]], [other["start"] + 1])
        self.assertEqual([r["start"] for r in self.node["innovation"]["ranges"]], [self.line])

    def test_range_outside_the_function_stops_the_build(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            _calltree.apply_innovation(self.payload, self.spec(end=self.node["end"] + 1))

    def test_stale_line_text_stops_the_build(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            _calltree.apply_innovation(self.payload, self.spec(text="not the source line"))

    def test_unknown_or_missing_role_stops_the_build(self):
        spec = self.spec()
        spec["functions"][0]["role"] = "novel"
        with self.assertRaisesRegex(ValueError, "role"):
            _calltree.apply_innovation(self.payload, spec)
        del spec["functions"][0]["role"]
        with self.assertRaisesRegex(ValueError, "role"):
            _calltree.validate_innovation(spec)

    def test_entries_are_checked_even_for_functions_without_a_card(self):
        spec = self.spec()
        spec["functions"][1]["ranges"] = [{"start": 5, "end": 2, "what": "inverted"}]
        with self.assertRaisesRegex(ValueError, "start <= end"):
            _calltree.validate_innovation(spec)

    def test_duplicate_function_and_missing_what_stop_the_build(self):
        spec = self.spec()
        spec["functions"].append(copy.deepcopy(spec["functions"][0]))
        with self.assertRaisesRegex(ValueError, "more than once"):
            _calltree.validate_innovation(spec)
        spec = self.spec(what="")
        with self.assertRaisesRegex(ValueError, "what"):
            _calltree.validate_innovation(spec)
        with self.assertRaisesRegex(ValueError, "functions"):
            _calltree.validate_innovation([])

    def test_rendered_page_embeds_marks_with_controls_hidden_by_default(self):
        _calltree.apply_innovation(self.payload, self.spec())
        with tempfile.TemporaryDirectory() as tmp:
            out = _render.render(HERE.parent / "templates" / "call_tree.html", self.payload, Path(tmp) / "call-tree.html")
            page = Path(out).read_text(encoding="utf-8")
        embedded = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(embedded["innovation"]["cards"], len(self.cards()))
        self.assertIn(".panel.innov {", page)
        self.assertRegex(page, r'<span id="legendinnov" hidden>')
        self.assertRegex(page, r'<button id="innovonly"[^>]* hidden>')


if __name__ == "__main__":
    unittest.main()
