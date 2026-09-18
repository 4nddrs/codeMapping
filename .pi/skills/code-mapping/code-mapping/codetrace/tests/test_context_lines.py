#!/usr/bin/env python3
"""Integrated coverage/profile/line capture regression tests (coverage required)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codetrace
import coverage


SOURCE = '''
import threading

def choose(flag):
    if flag:
        return 11
    return 22

def helper(value):
    return value + 1

def fails():
    raise ValueError("expected fixture failure")

def worker(results):
    result = choose(True)
    results.append(result)
    return result

def comprehension():
    values = [
        helper(value)
        for value in [1, 2]
    ]
    return values

def main():
    a = choose(True)
    b = choose(False)
    c = choose(True)
    d = choose(False)
    helper(0)
    helper(1)
    helper(2)
    helper(3)
    helper(4)
    helper(5)
    helper(6)
    helper(7)
    helper(8)
    helper(9)
    helper(10)
    helper(11)
    values = comprehension()
    try:
        fails()
    except ValueError:
        pass
    results = []
    thread = threading.Thread(target=worker, args=(results,))
    thread.start()
    thread.join()
    assert results == [11]
    return a, b, c, d, values, results

def thread_only():
    results = []
    thread = threading.Thread(target=worker, args=(results,))
    thread.start()
    thread.join()
    return results

def gated_worker(gate, results):
    gate.wait()
    results.append("continued after stop")
    return results
'''


class ContextLineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codetrace-context-lines-")
        self.root = Path(self.directory.name)
        self.project_file = self.root / "fixture.py"
        self.source = textwrap.dedent(SOURCE)
        self.project_file.write_text(self.source)
        spec = importlib.util.spec_from_file_location("context_line_fixture", str(self.project_file))
        self.project = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.project)

    def tearDown(self):
        self.directory.cleanup()

    def line(self, text):
        return next(i for i, source in enumerate(self.source.splitlines(), 1) if text in source)

    def run_capture(self, traced=True, use_coverage=True, target=None):
        collector = coverage.Coverage(source=[str(self.root)], branch=True,
                                      timid=True, concurrency=["thread"], data_file=None)
        tracer = codetrace.CallTracer(self.root, ["fixture.py"], Path(codetrace.__file__).parent)
        previous = sys.gettrace()
        previous_thread = getattr(threading, "_trace_hook", None)
        try:
            if use_coverage:
                collector.start()
            if traced:
                tracer.start()
            result = (target or self.project.main)()
        finally:
            if traced:
                tracer.stop()
            if use_coverage:
                collector.stop()
        self.assertIs(sys.gettrace(), previous)
        self.assertIs(getattr(threading, "_trace_hook", None), previous_thread)
        path = self.root / "graph.json"
        tracer.dump(path)
        graph = json.loads(path.read_text())
        self.assertEqual(graph["external_capture"]["recorder_errors"], 0)
        self.assertEqual(graph["external_capture"]["unfinished_samples"], 0)
        data = collector.get_data()
        filename = str(self.project_file)
        return graph, set(data.lines(filename) or []), set(map(tuple, data.arcs(filename) or [])), result

    def test_coverage_lines_arcs_unchanged_and_thread_lines_captured(self):
        _, expected_lines, expected_arcs, expected_result = self.run_capture(traced=False)
        graph, actual_lines, actual_arcs, result = self.run_capture()
        self.assertEqual(result, expected_result)
        self.assertEqual(actual_lines, expected_lines)
        self.assertEqual(actual_arcs, expected_arcs)
        worker = next(row for row in graph["instances"] if row["name"] == "worker")
        self.assertIn(self.line("result = choose(True)"), worker["executed_lines"])
        self.assertIn(self.line("results.append(result)"), worker["executed_lines"])
        self.assertIn(self.line("return result"), worker["executed_lines"])
        observed = set(line for row in graph["instances"] for line in row["executed_lines"])
        self.assertEqual(observed, actual_lines)
        self.assertFalse(any(row["target"]["source_path"] == str(self.project_file)
                             for row in graph["external_calls"]), "project callees must not become duplicate dependency nodes")

    def test_distinct_returns_and_sample_lines_remain_separate(self):
        graph, _, _, _ = self.run_capture()
        rows = [row for row in graph["instances"] if row["name"] == "choose"]
        yes = next(row for row in rows if row["cline"] == self.line("a = choose(True)"))
        no = next(row for row in rows if row["cline"] == self.line("b = choose(False)"))
        self.assertIn(self.line("return 11"), yes["executed_lines"])
        self.assertNotIn(self.line("return 22"), yes["executed_lines"])
        self.assertIn(self.line("return 22"), no["executed_lines"])
        self.assertNotIn(self.line("return 11"), no["executed_lines"])
        samples = next(row["samples"] for row in graph["calls"] if row["name"] == "choose")
        # values are kept per call-site card: each of choose's call sites (a-d and the
        # worker thread) keeps its own first call, in call order
        self.assertEqual(len(samples), len(rows))
        self.assertEqual(samples[0]["executed_lines"], yes["executed_lines"])
        self.assertEqual(samples[1]["executed_lines"], no["executed_lines"])
        failure = next(row["samples"][0] for row in graph["calls"] if row["name"] == "fails")
        self.assertEqual(failure["status"], "raised")
        self.assertNotIn("ret", failure)
        self.assertIn("builtins.ValueError", failure["exception_types"])

    def test_merged_helpers_keep_all_observed_incoming_edges(self):
        graph, _, _, _ = self.run_capture()
        merged_id = next(i for i, row in enumerate(graph["instances"])
                         if row["name"] == "helper" and row["merged"])
        merged = graph["instances"][merged_id]
        incoming = [edge for edge in graph["instance_edges"] if edge["to"] == merged_id]
        self.assertGreaterEqual(len(incoming), 5)
        self.assertEqual(sum(edge["count"] for edge in incoming), merged["count"])
        for n in range(8, 12):
            self.assertTrue(any(edge["cline"] == self.line("helper(%d)" % n) for edge in incoming))
        comp_id = next(i for i, row in enumerate(graph["instances"]) if row["name"] == "comprehension")
        comp_edge = next(edge for edge in incoming if edge["parent"] == comp_id)
        self.assertEqual(comp_edge["cline"], self.line("        helper(value)"))
        self.assertEqual(comp_edge["count"], 2)

    def test_synthetic_lines_belong_to_enclosing_invocation_sample(self):
        graph, _, _, _ = self.run_capture()
        row = next(row for row in graph["instances"] if row["name"] == "comprehension")
        sample = next(row["samples"][0] for row in graph["calls"] if row["name"] == "comprehension")
        self.assertIn(self.line("        helper(value)"), row["executed_lines"])
        self.assertEqual(sample["executed_lines"], row["executed_lines"])

    def test_threads_without_an_existing_trace_hook(self):
        exceptions = []
        original_hook = threading.excepthook
        threading.excepthook = lambda args: exceptions.append(args.exc_value)
        try:
            graph, _, _, result = self.run_capture(use_coverage=False, target=self.project.thread_only)
        finally:
            threading.excepthook = original_hook
        self.assertFalse(exceptions)
        self.assertEqual(result, [11])
        self.assertTrue(any(row["name"] == "worker" and row["executed_lines"] for row in graph["instances"]))

    def test_incompatible_coverage_c_tracer_fails_before_hook_mutation(self):
        collector = coverage.Coverage(source=[str(self.root)], branch=True,
                                      timid=False, concurrency=["thread"], data_file=None)
        tracer = codetrace.CallTracer(self.root, ["fixture.py"], Path(codetrace.__file__).parent)
        original_start = threading.Thread.start
        original_profile = sys.getprofile()
        collector.start()
        try:
            if type(sys.gettrace()).__name__ != "CTracer":
                self.skipTest("this coverage installation does not provide its C tracer")
            with self.assertRaisesRegex(RuntimeError, "timid=True"):
                tracer.start()
            self.assertIs(threading.Thread.start, original_start)
            self.assertIs(sys.getprofile(), original_profile)
        finally:
            collector.stop()

    def test_live_thread_continues_normally_without_recording_after_stop(self):
        class Gate:
            # Signal from an external helper after the project's gate.wait line
            # has executed; the project frame cannot advance until release.
            def __init__(self):
                self.started = threading.Event()
                self.release = threading.Event()

            def wait(self):
                self.started.set()
                self.release.wait()

        gate, results = Gate(), []
        collector = coverage.Coverage(source=[str(self.root)], branch=True,
                                      timid=True, concurrency=["thread"], data_file=None)
        tracer = codetrace.CallTracer(self.root, ["fixture.py"], Path(codetrace.__file__).parent)
        thread = threading.Thread(target=self.project.gated_worker, args=(gate, results))
        collector.start()
        tracer.start()
        try:
            thread.start()
            self.assertTrue(gate.started.wait(timeout=5), "worker never reached the controlled gate")
            record = next(row for row in tracer.inst_meta if row["tkey"][1] == "gated_worker")
            tracer.stop()
            frozen_lines = set(record["executed_lines"])
            self.assertIn(self.line("gate.wait()"), frozen_lines)
            self.assertNotIn(self.line('results.append("continued after stop")'), frozen_lines)
            gate.release.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(results, ["continued after stop"])
            self.assertEqual(set(record["executed_lines"]), frozen_lines)
        finally:
            gate.release.set()
            thread.join(timeout=5)
            if tracer._active:
                tracer.stop()
            collector.stop()
        self.assertIn(self.line('results.append("continued after stop")'),
                      collector.get_data().lines(str(self.project_file)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
