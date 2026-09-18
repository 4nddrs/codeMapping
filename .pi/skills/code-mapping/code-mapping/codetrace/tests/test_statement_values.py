#!/usr/bin/env python3
"""Values per statement: a sampled call records what each statement changed.

- A name reassigned on consecutive lines has its own value after each line,
  including lines that make no call (`x = x + [1]`, `y = x`).
- A call spanning several lines is one statement.
- A loop's later passes are coalesced, yet the value when the next statement
  first runs is exact (the loop's final total).
- In-place changes count (tensor `add_`, list `append`).
- Recording stops at MAX_STEPS and says where.
- With torch, a tensor's shape is recorded after each statement.
- Changes that keep the object: container items (dict/list and subclasses),
  numpy in-place writes, inference-mode tensors' in-place shape changes.
- A freed object's reused address does not hide a change; each changed name
  has its own summary budget; the call's last statement gets a final step; a
  resumed generator names the statement it resumed; a one-statement `while True`
  body counts its runs; an object whose __class__ raises does not drop the sample.
- Statements inside a `try` body, `match` cases and a backslash-continued `with`
  header each map to the right statement.
No coverage, data or GPU; the torch/numpy tests are skipped without them.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import codetrace

SOURCE = """
import collections

def helper(*args, **kwargs):
    return args[0] if args else None

def flow(n):
    x = [0] * n
    x = x + [1]
    y = len(x)
    x = helper(
        tuple(x),
        y,
    )
    z = x
    return z

def looping(items):
    total = 0
    for v in items:
        total = total + v
    after = total * 2
    return after

def inplace(items):
    size = len(items)
    items.append(7)
    grown = len(items)
    return size, grown

def items(batch, shape, dim):
    batch["obs"] = batch["obs"][:2]
    shape[dim] = 3
    out = collections.OrderedDict()
    out["a"] = 1
    out["b"] = 2
    return batch, shape, out

def floats(n):
    s = 0.0
    for i in range(n):
        s = s + 1.5
    avg = s / n
    return avg

def ends_with_change(items):
    size = len(items)
    items.append(3)

def gen(n):
    total = 0
    while total < n:
        got = yield total
        total = total + (got or 1)
    return total

def spin(it):
    x = 1
    try:
        while True:
            x = x * 2 + next(it)
    except StopIteration:
        pass
    return x

class Weird:
    @property
    def __class__(self):
        raise RuntimeError("proxy")

def weird(obj, n):
    m = n + 1
    return m

def batches(n):
    for i in range(n):
        batch = {"obs": [i] * 4}
        yield batch

def with_return(x):
    with open(__file__):
        y = x + 1
        return y

def finally_return(x):
    try:
        return x + 1
    finally:
        x = 0

def guarded(n):
    x = [0] * (2 * n)
    try:
        x = x[:n]
        x = x + [n]
        y = len(x) + 0
    except ValueError:
        y = None
    x = x[:3]
    return y, x

def continued_with(path):
    with open(path) as a, \\
            open(path) as b: n = 1
    after_with = n + 1
    return after_with

def many(n):
    a = 0
    b = 1
    c = 2
    d = 3
    e = 4
    return a + b + c + d + e + n
"""

MATCH_SOURCE = """
def dispatch(cmd, v):
    match cmd:
        case "a":
            z = v
            z = z + 1
        case "b" if v: z = -1
        case _:
            z = 0
    return z
"""

TORCH_SOURCE = """
import torch
import numpy as np

def np_scalars(rewards):
    total = np.float64(0.0)
    for r in rewards:
        total = total + r
    mean = total / len(rewards)
    return mean

def tensor_dicts(n):
    for i in range(n):
        batch = {"obs": torch.full((2, 3), float(i))}
    last = batch
    return last

def inference_inplace(x):
    with torch.inference_mode():
        sample = x * 2
        for _ in range(4):
            sample.mul_(0.5).add_(0.25)
        action = sample.clamp_(0.0, 0.6)
    return action

def inference(x):
    with torch.inference_mode():
        h = x * 2
        h.unsqueeze_(0)
        z = h
        tokens = torch.zeros(1, 1)
        for _ in range(6):
            tokens = torch.cat([tokens, tokens[:, :1]], dim=1)
        out = tokens[0]
    return z, out

def shapes(x):
    x = x.reshape(2, 6)
    x = x[:, 1:]
    memory = x
    x = torch.cat([x, x], dim=0)
    x.add_(1)
    return x, memory
"""


def value_after(sample, name, stmt):
    """The recorded value of `name` right after statement `stmt` first ran."""
    idx = sample["stmt_left"].get(str(stmt))
    if idx is None:
        return sample["locals"].get(name)
    best = sample["args"].get(name)
    for i, step in enumerate(sample["steps"]):
        if i < idx and name in step["vars"]:
            best = step["vars"][name]
    return best


def value_before(sample, name, stmt):
    idx = sample["stmt_first"][str(stmt)]
    best = sample["args"].get(name)
    for i, step in enumerate(sample["steps"]):
        if i < idx and name in step["vars"]:
            best = step["vars"][name]
    return best


class StatementValueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codetrace-statements-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def capture(self, name, source, target):
        path = self.root / (name + ".py")
        path.write_text(textwrap.dedent(source))
        self.lines = path.read_text().splitlines()
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tracer = codetrace.CallTracer(self.root, [name + ".py"], Path(codetrace.__file__).parent)
        tracer.start()
        try:
            target(module)
        finally:
            tracer.stop()
        out = self.root / (name + "-graph.json")
        tracer.dump(out)
        return json.loads(out.read_text())

    def line(self, text):
        return next(i for i, source in enumerate(self.lines, 1) if source.strip().startswith(text))

    def sample(self, graph, name):
        return next(c for c in graph["calls"] if c["name"].split(".")[-1] == name)["samples"][0]

    def test_reassigned_name_has_a_value_after_each_statement(self):
        graph = self.capture("flow_fixture", SOURCE, lambda m: m.flow(3))
        s = self.sample(graph, "flow")
        self.assertEqual(value_after(s, "x", self.line("x = [0] * n"))["n"], 3)
        self.assertEqual(value_after(s, "x", self.line("x = x + [1]"))["n"], 4)
        call = self.line("x = helper(")
        self.assertEqual(value_after(s, "x", call)["t"], "tuple")
        self.assertEqual(value_before(s, "x", call)["t"], "list")
        # the continuation lines belong to the call's statement
        self.assertNotIn(str(call + 1), s["stmt_first"])
        self.assertEqual(value_after(s, "z", self.line("z = x"))["t"], "tuple")
        self.assertEqual(s["exit_after"], self.line("return z"))
        self.assertTrue(all("after" in step for step in s["steps"]))

    def test_loop_passes_are_coalesced_but_exact_where_a_statement_first_runs(self):
        graph = self.capture("loop_fixture", SOURCE, lambda m: m.looping(list(range(10))))
        s = self.sample(graph, "looping")
        body = self.line("total = total + v")
        self.assertEqual(s["stmt_hits"][str(body)], 10)
        self.assertEqual(value_after(s, "total", body)["r"], "0")            # first pass: 0 + 0
        self.assertEqual(value_before(s, "total", self.line("after = total"))["r"], "45")
        recorded = sum(1 for step in s["steps"] if step["after"] == body and "total" in step["vars"])
        self.assertLessEqual(recorded, codetrace.MAX_PASSES)
        # the step that caught up with the skipped passes says so
        self.assertTrue(any(step.get("coalesced") for step in s["steps"]))
        self.assertFalse(any(k.startswith("_") for k in s), "internal state must not reach the payload")

    def test_in_place_change_is_recorded(self):
        graph = self.capture("inplace_fixture", SOURCE, lambda m: m.inplace([1, 2]))
        s = self.sample(graph, "inplace")
        stmt = self.line("items.append(7)")
        self.assertEqual(value_before(s, "items", stmt)["n"], 2)
        self.assertEqual(value_after(s, "items", stmt)["n"], 3)

    def test_recording_stops_at_max_steps_and_says_where(self):
        old = codetrace.MAX_STEPS
        codetrace.MAX_STEPS = 2
        try:
            graph = self.capture("cap_fixture", SOURCE, lambda m: m.many(1))
        finally:
            codetrace.MAX_STEPS = old
        s = self.sample(graph, "many")
        self.assertEqual(len(s["steps"]), 2)
        self.assertEqual(s["steps_truncated"], 2)
        late = s["stmt_first"][str(self.line("e = 4"))]
        self.assertGreater(late, s["steps_truncated"], "indexes past the cap must not look recorded")
        self.assertLessEqual(s["stmt_first"][str(self.line("b = 1"))], 2)

    def test_hot_loop_stays_bounded(self):
        graph = self.capture("hot_fixture", SOURCE, lambda m: m.looping(list(range(50000))))
        s = self.sample(graph, "looping")
        self.assertLessEqual(len(s["steps"]), 10)
        self.assertEqual(value_before(s, "total", self.line("after = total"))["r"], str(sum(range(50000))))

    def test_changes_that_keep_the_object(self):
        graph = self.capture("items_fixture", SOURCE, lambda m: m.items({"obs": [1, 2, 3, 4]}, [1, 1, 1], 0))
        s = self.sample(graph, "items")
        self.assertEqual(value_after(s, "batch", self.line('batch["obs"] = batch["obs"][:2]'))["items"]["obs"]["n"], 2)
        self.assertEqual(value_after(s, "shape", self.line("shape[dim] = 3"))["head"][0]["r"], "3")
        self.assertEqual(value_after(s, "out", self.line('out["a"] = 1'))["n"], 1)
        self.assertEqual(value_after(s, "out", self.line('out["b"] = 2'))["n"], 2)

    def test_reused_address_does_not_hide_a_change(self):
        graph = self.capture("floats_fixture", SOURCE, lambda m: m.floats(1001))
        s = self.sample(graph, "floats")
        self.assertEqual(value_before(s, "s", self.line("avg = s / n"))["r"], repr(1001 * 1.5))

    def test_each_name_has_its_own_summary_budget(self):
        old = codetrace.NODE_BUDGET
        codetrace.NODE_BUDGET = 40
        try:
            source = "def pair(n):\n    big, small = {str(i): list(range(5)) for i in range(50)}, n + 1\n    return small\n"
            graph = self.capture("budget_fixture", source, lambda m: m.pair(1))
        finally:
            codetrace.NODE_BUDGET = old
        s = self.sample(graph, "pair")
        self.assertEqual(value_after(s, "small", self.line("big, small ="))["r"], "2")

    def test_call_ending_statement_gets_a_final_step(self):
        graph = self.capture("ends_fixture", SOURCE, lambda m: m.ends_with_change([1, 2]))
        s = self.sample(graph, "ends_with_change")
        stmt = self.line("items.append(3)")
        self.assertIn(str(stmt), s["stmt_left"])
        self.assertEqual(value_after(s, "items", stmt)["n"], 3)
        self.assertIsNone(s["steps"][-1]["line"])

    def test_resumed_generator_names_the_resumed_statement(self):
        def drive(m):
            g = m.gen(5)
            next(g)
            g.send(2)
            g.send(2)
        graph = self.capture("gen_fixture", SOURCE, drive)
        samples = next(c for c in graph["calls"] if c["name"].split(".")[-1] == "gen")["samples"]
        resumed = samples[1]
        self.assertTrue(resumed["steps"])
        self.assertEqual(resumed["steps"][0]["after"], self.line("got = yield total"))
        self.assertEqual(value_after(resumed, "got", self.line("got = yield total"))["r"], "2")

    def test_single_statement_while_true_body_counts_runs(self):
        graph = self.capture("spin_fixture", SOURCE, lambda m: m.spin(iter([1, 2, 3])))
        s = self.sample(graph, "spin")
        body = self.line("x = x * 2 + next(it)")
        self.assertGreaterEqual(s["stmt_hits"][str(body)], 3)
        self.assertEqual(value_after(s, "x", body)["r"], "3")                # first run: 1 * 2 + 1

    def test_object_with_raising_class_keeps_the_sample(self):
        graph = self.capture("weird_fixture", SOURCE, lambda m: m.weird(m.Weird(), 1))
        s = self.sample(graph, "weird")
        self.assertEqual(value_after(s, "m", self.line("m = n + 1"))["r"], "2")

    def test_values_without_weak_references_after_skipped_passes(self):
        try:
            import numpy as np
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("numpy/torch not installed")
        for n in (4, 5, 8, 9):
            graph = self.capture("npscalar_%d" % n, TORCH_SOURCE, lambda m: m.np_scalars(np.arange(1, n + 1, dtype=np.float64)))
            s = self.sample(graph, "np_scalars")
            self.assertEqual(value_before(s, "total", self.line("mean = total"))["r"], repr(float(n * (n + 1) / 2)), n)
            graph = self.capture("tdict_%d" % n, TORCH_SOURCE, lambda m: m.tensor_dicts(n))
            s = self.sample(graph, "tensor_dicts")
            self.assertEqual(value_before(s, "batch", self.line("last = batch"))["items"]["obs"]["head"][0], float(n - 1), n)

    def test_inference_tensor_in_place_values(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch not installed")
        graph = self.capture("infer_inplace", TORCH_SOURCE, lambda m: m.inference_inplace(torch.ones(3)))
        s = self.sample(graph, "inference_inplace")
        self.assertEqual(value_before(s, "sample", self.line("action = sample.clamp_"))["head"][0], 0.59375)
        self.assertEqual(value_after(s, "sample", self.line("sample.mul_(0.5).add_(0.25)"))["head"][0], 1.25)

    def test_yield_in_a_loop_resumed_keeps_first_and_left_consistent(self):
        def drive(m):
            for _ in m.batches(3):
                pass
        graph = self.capture("yield_loop", SOURCE, drive)
        samples = next(c for c in graph["calls"] if c["name"].split(".")[-1] == "batches")["samples"]
        resumed = samples[1]
        y = self.line("yield batch")
        self.assertEqual(resumed["resumed"], y)
        self.assertIn("resumed_left", resumed)
        self.assertIn(str(y), resumed["stmt_first"])
        self.assertIn(str(y), resumed["stmt_left"])
        # the leave at suspension comes after the later entry, never before it
        self.assertGreaterEqual(resumed["stmt_left"][str(y)], resumed["stmt_first"][str(y)])
        self.assertLessEqual(resumed["resumed_left"], resumed["stmt_first"][str(y)])
        self.assertEqual(value_before(resumed, "batch", y)["items"]["obs"]["head"][0]["r"], "1")

    def test_exit_after_is_the_return_statement(self):
        graph = self.capture("with_ret", SOURCE, lambda m: m.with_return(1))
        s = self.sample(graph, "with_return")
        self.assertEqual(s["exit_after"], self.line("return y"))
        self.assertEqual(s["stmt_hits"][str(self.line("return y"))], 1)
        graph = self.capture("fin_ret", SOURCE, lambda m: m.finally_return(1))
        s = self.sample(graph, "finally_return")
        self.assertEqual(s["exit_after"], self.line("return x + 1"))
        self.assertEqual(s["stmt_hits"][str(self.line("return x + 1"))], 1)

    def test_numpy_writes_past_the_first_elements(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        source = "import numpy as np\ndef tail(a):\n    a[-1] = 7.0\n    total = a.sum()\n    return total\n"
        graph = self.capture("numpy_tail", source, lambda m: m.tail(np.zeros(64)))
        s = self.sample(graph, "tail")
        self.assertEqual(value_before(s, "a", self.line("total = a.sum()"))["head"][0], 0.0)
        self.assertIn(str(self.line("a[-1] = 7.0")), s["stmt_left"])
        self.assertTrue(any("a" in st["vars"] and st["after"] == self.line("a[-1] = 7.0") for st in s["steps"]))

    def test_statements_inside_a_try_body_have_their_own_values(self):
        graph = self.capture("try_body", SOURCE, lambda m: m.guarded(4))
        s = self.sample(graph, "guarded")
        first = self.line("x = x[:n]")
        for text in ("x = x[:n]", "x = x + [n]", "y = len(x) + 0"):
            self.assertIn(str(self.line(text)), s["stmt_first"], text)
        self.assertEqual(value_after(s, "x", first)["n"], 4)
        self.assertEqual(value_after(s, "x", self.line("x = x + [n]"))["n"], 5)
        self.assertEqual(value_after(s, "x", self.line("x = x[:3]"))["n"], 3)
        self.assertEqual(value_before(s, "x", first)["n"], 8)

    def test_match_cases_are_their_own_statements(self):
        if sys.version_info < (3, 10):
            self.skipTest("match needs Python 3.10+")
        graph = self.capture("match_cases", MATCH_SOURCE, lambda m: [m.dispatch("a", 1), m.dispatch("c", 0)])
        samples = next(c for c in graph["calls"] if c["name"] == "dispatch")["samples"]
        first = samples[0]
        self.assertIn(str(self.line('case "a":')), first["stmt_first"])
        self.assertEqual(value_after(first, "z", self.line("z = v"))["r"], "1")
        self.assertEqual(value_after(first, "z", self.line("z = z + 1"))["r"], "2")
        other = samples[1]
        self.assertNotIn(str(self.line("z = v")), other["stmt_first"])
        self.assertEqual(value_after(other, "z", self.line("z = 0"))["r"], "0")

    def test_continued_with_header_keeps_its_same_line_body(self):
        graph = self.capture("with_continued", SOURCE, lambda m: m.continued_with(m.__file__))
        s = self.sample(graph, "continued_with")
        header = self.line("with open(path) as a")
        self.assertTrue(self.lines[header - 1].rstrip().endswith("\\"), "the fixture keeps its continuation")
        self.assertNotIn(str(header + 1), s["stmt_first"])
        self.assertEqual(value_before(s, "n", self.line("after_with = n + 1"))["r"], "1")

    def test_numpy_in_place_writes(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        source = "import numpy as np\ndef arr(a):\n    a += 5\n    a[0] = 99\n    total = a.sum()\n    return total\n"
        import numpy as np
        graph = self.capture("numpy_fixture", source, lambda m: m.arr(np.zeros(4)))
        s = self.sample(graph, "arr")
        self.assertEqual(value_after(s, "a", self.line("a += 5"))["head"][:2], [5.0, 5.0])
        self.assertEqual(value_after(s, "a", self.line("a[0] = 99"))["head"][:2], [99.0, 5.0])

    def test_inference_mode_tensors(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch not installed")
        graph = self.capture("inference_fixture", TORCH_SOURCE, lambda m: m.inference(torch.zeros(2, 8)))
        s = self.sample(graph, "inference")
        self.assertEqual(value_after(s, "h", self.line("h.unsqueeze_(0)"))["shape"], [1, 2, 8])
        self.assertEqual(value_before(s, "tokens", self.line("out = tokens[0]"))["shape"], [1, 7])

    def test_tensor_shape_after_each_statement(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch not installed")
        graph = self.capture("torch_statements", TORCH_SOURCE, lambda m: m.shapes(torch.zeros(12)))
        s = self.sample(graph, "shapes")
        self.assertEqual(value_after(s, "x", self.line("x = x.reshape"))["shape"], [2, 6])
        self.assertEqual(value_after(s, "x", self.line("x = x[:, 1:]"))["shape"], [2, 5])
        self.assertEqual(value_after(s, "memory", self.line("memory = x"))["shape"], [2, 5])
        cat = self.line("x = torch.cat")
        self.assertEqual(value_after(s, "x", cat)["shape"], [4, 5])
        add = self.line("x.add_(1)")
        self.assertEqual(value_before(s, "x", add)["head"][0], 0.0)
        self.assertEqual(value_after(s, "x", add)["head"][0], 1.0)


if __name__ == "__main__":
    unittest.main()
