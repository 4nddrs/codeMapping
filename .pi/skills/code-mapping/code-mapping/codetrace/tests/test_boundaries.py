#!/usr/bin/env python3
"""Real profiler regression tests; run with Python, optionally with torch installed.

No model downloads, CUDA, or project datasets are required. The temporary project
is intentionally distinct from its dependency, so missing boundary observation
cannot be hidden by simply tracing all source as project code.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _boundaries import BoundaryRecorder
from codetrace import summarize


LIBRARY = '''
def leaf(value):
    return value + 1

def returns_none(value):
    return None

def fails(value):
    raise ValueError("expected fixture error")

def delegates_failure(value):
    return fails(value)

def generator():
    yield 1
    yield 2

def yields_none():
    yield None

def closes_after_value():
    yield 0

def wrapper(value):
    return leaf(value)

class Callable:
    def __call__(self, value):
        return value + 2

class Factory:
    @staticmethod
    def operation(value):
        return value + 3

    @classmethod
    def factory(cls, value):
        return cls.operation(value)
'''

PROJECT = '''
import boundary_test_dependency as lib

def branches():
    a, b = lib.leaf(1), lib.leaf(2)
    c = lib.leaf(lib.leaf(3))
    skipped = False and lib.leaf(99)
    empty = [lib.leaf(v) for v in []]
    populated = [lib.leaf(v) for v in [4, 5]]
    native = [len(v) for v in [[1], [1, 2]]]
    dynamic = lib.leaf
    d = dynamic(6)
    return a, b, c, populated, native, d

def exceptions():
    none = lib.returns_none(1)
    for function in (lib.fails, lib.delegates_failure):
        try:
            function(1)
        except ValueError:
            pass
    try:
        [].pop()
    except IndexError:
        pass
    values = list(lib.generator())
    return none, values

def protocols():
    a = lib.Callable()(1)
    b = lib.Factory.operation(a)
    c = lib.Factory.factory(b)
    return lib.wrapper(c)

def context_call():
    return lib.returns_none(1)

def generator_ambiguity():
    none = lib.yields_none()
    assert next(none) is None
    none.close()
    assert none.gi_frame is None
    value = lib.closes_after_value()
    assert next(value) == 0
    value.close()
    assert value.gi_frame is None
'''

TORCH_PROJECT = '''
import torch

class Model(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.input_emb = torch.nn.Linear(3, 4)
        self.drop = torch.nn.Dropout(0.1)

    def forward(self, sample):
        x = self.input_emb(sample)
        x = self.drop(x)
        y = torch.cat([x, x], dim=-1)
        z = y.reshape(2, 8)
        q = torch.cat([x, x], dim=-1).reshape(2, 8)
        return z + q

def main():
    model = Model()
    x = torch.ones(2, 3)
    for _ in range(3):
        model(x)
'''


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codetrace-boundaries-")
        self.root = Path(self.directory.name)
        self.library_file = self.root / "dependency.py"
        self.project_file = self.root / "project.py"
        self.library_file.write_text(textwrap.dedent(LIBRARY))
        self.project_file.write_text(textwrap.dedent(PROJECT))
        self.library = load_file("boundary_test_dependency", self.library_file)
        self.project = load_file("boundary_test_project", self.project_file)

    def tearDown(self):
        sys.modules.pop("boundary_test_dependency", None)
        sys.modules.pop("boundary_test_project", None)
        self.directory.cleanup()

    def capture(self, function, modes=(None,), **options):
        frames, instances = {}, {}
        current_mode = [None]
        project_path = str(self.project_file)
        recorder = BoundaryRecorder(
            self.root, frames, lambda filename: filename == project_path,
            summarize, context=lambda frame: current_mode[0], **options)

        def profile(frame, event, arg):
            # Minimal project-instance hook; deliberately omit synthetic frames
            # to exercise the recorder's comprehension/lambda forwarding path.
            if (event == "call" and frame.f_code.co_filename == project_path
                    and not frame.f_code.co_name.startswith("<")):
                parent = frames.get(id(frame.f_back), -1)
                line = frame.f_back.f_lineno if frame.f_back is not None else 0
                key = (frame.f_code, parent, line)
                frames[id(frame)] = instances.setdefault(key, len(instances))
            recorder.profile(frame, event, arg)
            if event == "return":
                frames.pop(id(frame), None)

        old = sys.getprofile()
        try:
            sys.setprofile(profile)
            for mode in modes:
                current_mode[0] = mode
                function()
        finally:
            sys.setprofile(old)
        data = recorder.dump()
        self.assertEqual(data["external_capture"]["recorder_errors"], 0)
        self.assertEqual(data["external_capture"]["unfinished_samples"], 0)
        return data

    def named(self, data, suffix):
        return [r for r in data["external_calls"]
                if r["target"]["name"].endswith(suffix)]

    def test_same_line_nested_short_circuit_and_comprehension(self):
        data = self.capture(self.project.branches)
        rows = self.named(data, "leaf")
        self.assertEqual(sum(r["count"] for r in rows), 7)
        self.assertFalse(any("99" in r["expression"] for r in rows))
        self.assertFalse(any("for v in []" in r["expression"] for r in rows))
        single = [r for r in rows if r["expression"] in ("lib.leaf(1)", "lib.leaf(2)")]
        self.assertEqual(len(single), 2)
        self.assertEqual(single[0]["cline"], single[1]["cline"])
        self.assertNotEqual(single[0]["caller_bytecode_offset"], single[1]["caller_bytecode_offset"])
        self.assertTrue(all(r["expression_exact"] for r in single))
        self.assertEqual(len([r for r in rows if "lib.leaf(3)" in r["expression"]]), 2)
        comprehension = [r for r in rows if r["expression"] == "lib.leaf(v)"]
        self.assertEqual(len(comprehension), 1)
        self.assertEqual(comprehension[0]["count"], 2)
        # Python 3.12+ inlines comprehensions; older interpreters use a real
        # synthetic frame that must be forwarded without inventing a card.
        has_synthetic = any(getattr(c, "co_name", None) == "<listcomp>"
                            for c in self.project.branches.__code__.co_consts)
        if has_synthetic:
            self.assertIn("<listcomp>", comprehension[0]["via"])
            self.assertTrue(comprehension[0].get("synthetic_caller"))
        native = self.named(data, "len")
        self.assertEqual(sum(r["count"] for r in native), 2)
        if has_synthetic:
            self.assertTrue(native[0].get("synthetic_caller"))
        self.assertEqual(len([r for r in rows if r["expression"] == "dynamic(6)"]), 1)

    def test_python_native_exceptions_none_and_generator(self):
        data = self.capture(self.project.exceptions)
        none = self.named(data, "returns_none")[0]
        self.assertEqual(none["outcomes"]["returned"], 1)
        self.assertEqual(none["samples"][0]["ret"]["t"], "NoneType")
        for suffix in ("fails", "delegates_failure", "list.pop"):
            record = self.named(data, suffix)[0]
            self.assertEqual(record["outcomes"]["raised"], 1)
            self.assertNotIn("ret", record["samples"][0])
            self.assertIn("exception_unavailable", record["samples"][0])
        generator = self.named(data, "generator")[0]
        self.assertEqual(generator["outcomes"]["suspended"], 2)
        self.assertEqual(generator["outcomes"]["returned"], 1)
        self.assertIn("yielded", generator["samples"][0])

    def test_wrappers_static_class_and_callable_boundaries(self):
        data = self.capture(self.project.protocols)
        for suffix in ("Callable.__call__", "Factory.operation", "Factory.factory", "wrapper"):
            record = self.named(data, suffix)[0]
            self.assertEqual(record["outcomes"]["returned"], 1)
            self.assertTrue(record["target"]["source_available"])
        self.assertFalse(self.named(data, "leaf"), "dependency implementation must not be recursively expanded")

    def test_actual_none_yield_and_generator_close_are_not_claimed_as_yields(self):
        data = self.capture(self.project.generator_ambiguity)
        self.assertEqual(data["external_capture"]["schema"], 2)
        self.assertEqual(data["external_capture"]["none_suspension_outcomes"], "unknown")
        none = self.named(data, "yields_none")
        # Some newer Python interpreters emit no generator-frame profile event
        # for close(). The fixture asserts the generator really closed either
        # way; do not invent an extra event on those versions.
        self.assertIn(len(none), (1, 2))
        for record in none:
            self.assertEqual(record["outcomes"]["unknown"], 1)
            self.assertNotIn("yielded", record["samples"][0])
            self.assertNotIn("ret", record["samples"][0])
            self.assertIn("close()", record["samples"][0]["ret_unavailable"])
        value = self.named(data, "closes_after_value")
        self.assertIn(len(value), (1, 2))
        self.assertEqual(sum(row["outcomes"]["suspended"] for row in value), 1)
        self.assertEqual(sum(row["outcomes"]["unknown"] for row in value), len(value) - 1)
        yielded = [sample["yielded"] for row in value for sample in row["samples"] if "yielded" in sample]
        self.assertEqual(yielded, [{"t": "int", "r": "0"}])

    def test_bounded_context_samples_and_caps(self):
        data = self.capture(self.project.context_call, modes=(1, 1, 1, 2, 2, 2))
        row = data["external_calls"][0]
        self.assertEqual(row["count"], 6)
        self.assertEqual(len(row["samples"]), 4)
        self.assertEqual([c["count"] for c in row["contexts"]], [3, 3])
        limited = self.capture(self.project.branches, max_records=2)
        self.assertEqual(len(limited["external_calls"]), 2)
        self.assertGreater(limited["external_capture"]["dropped_calls"], 0)
        self.assertTrue(limited["external_capture"]["dropped_examples"])
        contexts = self.capture(self.project.context_call, modes=(1, 1, 2, 2), max_contexts=1)
        self.assertEqual(contexts["external_capture"]["context_overflow_calls"], 2)
        self.assertEqual(len(contexts["external_calls"][0]["samples"]), 2)

    def test_excluded_instrumentation_is_counted(self):
        data = self.capture(self.project.context_call, exclude=lambda filename: filename == str(self.library_file))
        self.assertFalse(data["external_calls"])
        self.assertEqual(data["external_capture"]["excluded_instrumentation_calls"], 1)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "torch is optional; run in the project's torch environment")
    def test_torch_linear_dispatch_native_tensor_calls_and_shapes(self):
        self.project_file.write_text(textwrap.dedent(TORCH_PROJECT))
        self.project = load_file("boundary_test_project", self.project_file)
        data = self.capture(self.project.main)
        linear = self.named(data, "Linear.forward")[0]
        self.assertEqual(linear["count"], 3)
        self.assertEqual(linear["expression"], "self.input_emb(sample)")
        self.assertIn("def forward", linear["target"]["source"])
        self.assertEqual(linear["samples"][0]["args"]["input"]["shape"], [2, 3])
        self.assertEqual(linear["samples"][0]["ret"]["shape"], [2, 4])
        self.assertEqual(self.named(data, "Dropout.forward")[0]["count"], 3)
        self.assertFalse(self.named(data, "_call_impl"))
        self.assertFalse(self.named(data, "Model.forward"), "project forward must not become an external duplicate")
        cats = self.named(data, ".cat")
        self.assertEqual(len(cats), 2)
        self.assertTrue(all(r["target"]["kind"] == "native" for r in cats))
        for row in self.named(data, "Tensor.reshape"):
            self.assertEqual(row["samples"][0]["receiver"]["shape"], [2, 8])
            self.assertIn("ret_unavailable", row["samples"][0])
            self.assertNotIn("ret", row["samples"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
