#!/usr/bin/env python3
"""Tracer regressions: threads, sampling cost, and nn.Module structure.

- Several threads calling project code must not crash in the profile hook.
- A hot function must not summarize the arguments of calls whose values are not kept.
- A torch module value carries a "module" key; the dumped module table holds its
  children, extra_repr, parameter shapes and observed input -> output shapes.
- A sampled frame takes value steps at library calls too (`self.fc(h)`).
The torch test is skipped when torch is not installed. No coverage, data or GPU.
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
import threading

def work(x):
    y = x + 1
    return y

def spin(n, errors):
    try:
        for i in range(n):
            work(i)
    except Exception as exc:
        errors.append(repr(exc))

def threaded(n_threads, n_calls):
    errors = []
    threads = [threading.Thread(target=spin, args=(n_calls, errors)) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors

def hot(batch, cfg):
    return len(batch) + len(cfg)

def hot_loop(n):
    batch = [list(range(20)) for _ in range(20)]
    cfg = {"k%d" % i: i for i in range(40)}
    total = 0
    for _ in range(n):
        total += hot(batch, cfg)
    return total
"""

TORCH_SOURCE = """
import torch
from torch import nn

class Enc(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(4, 8), nn.ReLU(), nn.Linear(8, 8))
        self.fc = nn.Linear(8, 2)

    def forward(self, x):
        h = self.encoder(x)
        return self.fc(h)

def run():
    model = Enc()
    x = torch.zeros(3, 4)
    out = model(x)
    out = model(x)
    return out
"""


class TracerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codetrace-round3-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def load(self, name, source):
        path = self.root / (name + ".py")
        path.write_text(textwrap.dedent(source))
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def capture(self, name, target):
        tracer = codetrace.CallTracer(self.root, [name + ".py"], Path(codetrace.__file__).parent)
        previous = sys.gettrace()
        tracer.start()
        try:
            result = target()
        finally:
            tracer.stop()
        self.assertIs(sys.gettrace(), previous)
        out = self.root / (name + "-graph.json")
        tracer.dump(out)
        return json.loads(out.read_text()), result

    def test_threads_calling_project_code_do_not_crash_the_hook(self):
        module = self.load("threads_fixture", SOURCE)
        old = sys.getswitchinterval()
        sys.setswitchinterval(1e-5)
        try:
            graph, errors = self.capture("threads_fixture", lambda: module.threaded(6, 3000))
        finally:
            sys.setswitchinterval(old)
        self.assertEqual(errors, [])
        work = next(c for c in graph["calls"] if c["name"] == "work")
        # call counters are not locked (a lock per call would slow every trace),
        # so threads switching this often may lose a few increments
        self.assertGreater(work["count"], 0.9 * 6 * 3000)
        self.assertLessEqual(work["count"], 6 * 3000)
        per_card = {}
        for sample in work["samples"]:
            per_card[sample["inst"]] = per_card.get(sample["inst"], 0) + 1
        self.assertTrue(per_card)
        self.assertTrue(all(n <= codetrace.MAX_SAMPLES for n in per_card.values()), per_card)

    def test_calls_that_are_not_kept_do_not_summarize_arguments(self):
        module = self.load("cost_fixture", SOURCE)
        calls = [0]
        original = codetrace.summarize_locals

        def counting(f_locals):
            calls[0] += 1
            return original(f_locals)

        codetrace.summarize_locals = counting
        try:
            graph, _ = self.capture("cost_fixture", lambda: module.hot_loop(2000))
        finally:
            codetrace.summarize_locals = original
        hot = next(c for c in graph["calls"] if c["name"] == "hot")
        self.assertEqual(hot["count"], 2000)
        self.assertLess(calls[0], 100, "argument summaries must stay bounded by kept samples, not calls")

    def test_module_structure_and_observed_shapes_are_recorded(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("torch not installed")
        module = self.load("torch_fixture", TORCH_SOURCE)
        graph, _ = self.capture("torch_fixture", module.run)
        # co_qualname only exists on Python 3.11+
        forward = next(c for c in graph["calls"] if c["name"] in ("Enc.forward", "forward"))
        init = next(c for c in graph["calls"] if c["name"] in ("Enc.__init__", "__init__"))
        # registered while still empty (at __init__ entry): children are found later
        self.assertIn("module", init["samples"][0]["args"]["self"])
        self_value = forward["samples"][0]["args"]["self"]
        self.assertIn("module", self_value)
        # `return self.fc(h)` only calls into torch: the value step is still taken there
        steps = forward["samples"][0].get("steps") or []
        self.assertIn(("h", [3, 8]), [(k, v.get("shape")) for step in steps for k, v in step["vars"].items()])
        self.assertEqual(self_value["module"], init["samples"][0]["args"]["self"]["module"])
        table = graph["modules"]
        enc = table[self_value["module"]]
        self.assertEqual(enc["t"], "Enc")
        self.assertEqual(set(enc["children"]), {"encoder", "fc"})
        self.assertEqual(enc["n_params"], 4 * 8 + 8 + 8 * 8 + 8 + 8 * 2 + 2)
        self.assertEqual(enc["calls"], [{"in": [[3, 4]], "out": [3, 2]}])
        seq = table[enc["children"]["encoder"]]
        self.assertEqual(seq["t"], "Sequential")
        self.assertEqual(list(seq["children"]), ["0", "1", "2"])
        first = table[seq["children"]["0"]]
        self.assertEqual(first["extra"], "in_features=4, out_features=8, bias=True")
        self.assertEqual(first["params"]["weight"], [8, 4])
        # the first call already has shapes: children are registered at the parent's forward
        self.assertEqual(first["calls"], [{"in": [[3, 4]], "out": [3, 8]}])
        self.assertEqual(seq["calls"], [{"in": [[3, 4]], "out": [3, 8]}])
        self.assertEqual(table[seq["children"]["1"]]["calls"], [{"in": [[3, 8]], "out": [3, 8]}])
        self.assertEqual(table[enc["children"]["fc"]]["calls"][0]["out"], [3, 2])
        import torch.nn.modules.module as torch_module
        self.assertFalse(getattr(torch_module, "_global_forward_hooks", {}), "no torch hook is installed")
        self.assertFalse(getattr(torch_module, "_global_forward_pre_hooks", {}), "no torch hook is installed")


if __name__ == "__main__":
    unittest.main()
