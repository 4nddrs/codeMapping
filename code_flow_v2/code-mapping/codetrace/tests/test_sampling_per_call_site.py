#!/usr/bin/env python3
"""Values are sampled per call-site card, not once per function.

A function called from three places gets three cards; each card must keep the
first MAX_SAMPLES calls made from its own call site. Before the fix only the
first MAX_SAMPLES calls of the whole function kept values, so the later cards
were empty. Needs no coverage, datasets or GPU.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import codetrace

SOURCE = """
def work(x):
    y = x * 2
    return y


def site_a():
    out = []
    for i in range(3):
        out.append(work(i))
    return out


def site_b():
    total = 0
    for i in range(4):
        total += work(i + 10)
    return total


def main():
    site_a()
    site_b()
    return work(100)
"""


class PerCallSiteSamplingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codetrace-sampling-")
        self.root = Path(self.directory.name)
        path = self.root / "fixture_sites.py"
        path.write_text(textwrap.dedent(SOURCE))
        spec = importlib.util.spec_from_file_location("fixture_sites", str(path))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.directory.cleanup()

    def capture(self):
        tracer = codetrace.CallTracer(self.root, ["fixture_sites.py"], Path(codetrace.__file__).parent)
        previous, previous_thread = sys.gettrace(), getattr(threading, "_trace_hook", None)
        tracer.start()
        try:
            self.module.main()
        finally:
            tracer.stop()
        self.assertIs(sys.gettrace(), previous)
        self.assertIs(getattr(threading, "_trace_hook", None), previous_thread)
        out = self.root / "graph.json"
        tracer.dump(out)
        return json.loads(out.read_text())

    def test_each_call_site_card_keeps_its_own_first_samples(self):
        graph = self.capture()
        work = next(c for c in graph["calls"] if c["name"] == "work")
        self.assertEqual(work["count"], 8)
        cards = [i for i, meta in enumerate(graph["instances"]) if meta["name"] == "work"]
        self.assertEqual(len(cards), 3, "site_a loop, site_b loop and main each get a card")
        kept = {}
        for sample in work["samples"]:
            kept.setdefault(sample["inst"], []).append(sample["n"])
        for card in cards:
            self.assertIn(card, kept, f"card for call line {graph['instances'][card]['cline']} has no values")
            self.assertLessEqual(len(kept[card]), codetrace.MAX_SAMPLES)
        # site_a makes calls 1-3, site_b calls 4-7, main call 8: each keeps its own first two.
        self.assertEqual(sorted(n for calls in kept.values() for n in calls), [1, 2, 4, 5, 8])


if __name__ == "__main__":
    unittest.main()
