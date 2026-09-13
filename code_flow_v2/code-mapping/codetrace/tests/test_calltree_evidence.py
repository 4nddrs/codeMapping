#!/usr/bin/env python3
"""Renderer regressions built from a real, temporary traced Python execution.

Run this file directly or use unittest discovery from the tests directory.
Requires coverage, like test_context_lines.py; no project datasets or GPU.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import _calltree
import test_context_lines as _capture_fixture


class CalltreeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = _capture_fixture.ContextLineTests(methodName="test_distinct_returns_and_sample_lines_remain_separate")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.graph, lines, arcs, _ = self.fixture.run_capture()
        # Feed the renderer the exact lines/arcs returned by coverage's public
        # data API in that same execution. Missing lines are immaterial to these
        # assertions; no synthetic executions or guessed call records are used.
        self.coverage = {"files": {"fixture.py": {
            "executed_lines": sorted(lines),
            "executed_branches": [list(arc) for arc in sorted(arcs) if min(arc) > 0],
            "missing_lines": [], "missing_branches": [],
        }}}

    def build(self, graph=None, entry="main"):
        return _calltree.build(
            root=self.fixture.root, cg=self.graph if graph is None else graph,
            cov=self.coverage, command="python fixture.py", outcome="fixture passed",
            title="Observed renderer regression", brand="Tests", entry=entry,
            important=("choose", "helper", "worker"),
        )

    def test_distinct_return_contexts_and_samples_are_not_combined(self):
        payload = self.build()
        nodes = {node["raw_instance"]: node for node in payload["nodes"] if "raw_instance" in node}
        contexts = {}
        for raw_id, record in enumerate(self.graph["instances"]):
            if record["name"] != "choose":
                continue
            if record["cline"] == self.fixture.line("a = choose(True)"):
                contexts[True] = nodes[raw_id]
            elif record["cline"] == self.fixture.line("b = choose(False)"):
                contexts[False] = nodes[raw_id]
        yes, no = contexts[True], contexts[False]
        first, second = self.fixture.line("return 11"), self.fixture.line("return 22")
        self.assertEqual(yes["coverage_scope"], "call_site_group")
        self.assertEqual(no["coverage_scope"], "call_site_group")
        self.assertIn(first, yes["ex"])
        self.assertNotIn(second, yes["ex"])
        self.assertIn(second, no["ex"])
        self.assertNotIn(first, no["ex"])
        self.assertTrue({first, second}.issubset(yes["run_ex"]))
        self.assertEqual(yes["samples"][0]["executed_lines"], yes["ex"])
        self.assertEqual(no["samples"][0]["executed_lines"], no["ex"])

    def test_merged_helper_edges_match_only_observed_instances(self):
        payload = self.build()
        nodes = {node["raw_instance"]: node for node in payload["nodes"] if "raw_instance" in node}
        merged_id = next(i for i, record in enumerate(self.graph["instances"])
                         if record["name"] == "helper" and record["merged"])
        merged_node = nodes[merged_id]
        self.assertEqual(merged_node["coverage_scope"], "merged_call_sites")
        expected = {
            (nodes[edge["parent"]]["id"], edge["cline"], nodes[edge["to"]]["id"], edge["count"])
            for edge in self.graph["instance_edges"]
            if edge["to"] == merged_id and edge["parent"] in nodes
        }
        actual = {(edge["from"], edge["line"], edge["to"], edge["n"])
                  for edge in payload["edges"] if edge["to"] == merged_node["id"]}
        self.assertEqual(actual, expected)
        self.assertEqual(sum(edge[3] for edge in actual), merged_node["calls"])
        self.assertTrue(all(edge["provenance"] == "instance_edge" for edge in payload["edges"]
                            if edge["to"] == merged_node["id"]))

    def test_every_observed_external_record_is_accounted_for(self):
        payload = self.build()
        raw = {row["id"]: row for row in self.graph["external_calls"]}
        self.assertTrue(raw)
        drawn = {node["boundary"]["id"]: node for node in payload["nodes"] if node.get("boundary")}
        excluded = {row["id"]: row for row in payload["boundary_audit"]["excluded"]}
        self.assertFalse(set(drawn) & set(excluded))
        self.assertEqual(set(raw), set(drawn) | set(excluded))
        self.assertEqual(payload["boundary_audit"]["recorded"], len(raw))
        self.assertEqual(payload["boundary_audit"]["rendered"], len(drawn))
        self.assertFalse(excluded, "every fixture dependency caller belongs to the selected main tree")
        project = {node["raw_instance"]: node for node in payload["nodes"] if "raw_instance" in node}
        for boundary_id, node in drawn.items():
            record = raw[boundary_id]
            links = [edge for edge in payload["edges"] if edge.get("boundary_id") == boundary_id]
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0]["from"], project[record["parent"]]["id"])
            self.assertEqual(links[0]["to"], node["id"])
            self.assertEqual(links[0]["line"], record["cline"])
            self.assertEqual(links[0]["n"], record["count"])
            self.assertEqual(links[0]["provenance"], "external_call")
            self.assertEqual(node["samples"], record["samples"])
            self.assertEqual(node["boundary"]["target"], record["target"])

    def test_dependency_reference_source_has_no_false_internal_coverage(self):
        payload = self.build()
        boundaries = [node for node in payload["nodes"] if node.get("boundary")]
        self.assertTrue(any(node["boundary"]["kind"] == "native" for node in boundaries))
        self.assertTrue(any(node["boundary"]["kind"] == "python" for node in boundaries))
        self.assertEqual(payload["totals"]["lines"], sum(node["nlines"] for node in payload["nodes"] if not node.get("boundary")))
        self.assertEqual(payload["totals"]["reference_lines"], sum(node["nlines"] for node in boundaries))
        self.assertGreater(payload["totals"]["reference_lines"], 0)
        self.assertEqual(payload["totals"]["executed"], sum(len(node["ex"]) for node in payload["nodes"] if not node.get("boundary")))
        for node in boundaries:
            self.assertEqual(node["coverage_scope"], "boundary_only")
            for field in ("ex", "mi", "partial", "run_ex"):
                self.assertEqual(node[field], [], (node["name"], field))
            self.assertFalse(any(edge["from"] == node["id"] for edge in payload["edges"]),
                             "direct dependency boundaries must not invent nested library execution")
            if node["boundary"]["kind"] == "native":
                self.assertIn("source is unavailable", node["src"])
                for sample in node["samples"]:
                    self.assertNotIn("ret", sample)
                    self.assertIn("args_unavailable", sample)

    def test_boundaries_outside_selected_entry_have_explicit_exclusions(self):
        payload = self.build(entry="worker")
        recorded = {row["id"] for row in self.graph["external_calls"]}
        rendered = {node["boundary"]["id"] for node in payload["nodes"] if node.get("boundary")}
        exclusions = payload["boundary_audit"]["excluded"]
        self.assertTrue(exclusions, "main's dependency calls are outside the worker subtree")
        self.assertTrue(rendered, "the actual worker list.append boundary remains reachable")
        self.assertEqual(recorded, rendered | {row["id"] for row in exclusions})
        self.assertTrue(all("outside the selected entry" in row["reason"] for row in exclusions))

    def test_old_instance_graph_falls_back_to_whole_run_coverage(self):
        old = copy.deepcopy(self.graph)
        old.pop("line_capture", None)
        old.pop("instance_edges", None)
        old.pop("external_calls", None)
        old.pop("external_capture", None)
        for record in old["instances"]:
            record.pop("executed_lines", None)
            record.pop("executed_arcs", None)
        for record in old["calls"]:
            for sample in record.get("samples", []):
                sample.pop("executed_lines", None)
        payload = self.build(old)
        self.assertEqual(payload["coverage_scope"], "whole_run")
        self.assertIn("Per-invocation line coverage was not recorded", payload["coverage_note"])
        self.assertTrue(all(node["coverage_scope"] == "whole_run" for node in payload["nodes"]))
        first, second = self.fixture.line("return 11"), self.fixture.line("return 22")
        for node in payload["nodes"]:
            if node["name"] == "choose":
                self.assertTrue({first, second}.issubset(node["ex"]))

    def test_old_function_graph_has_no_exact_context_claim(self):
        old = copy.deepcopy(self.graph)
        for key in ("instances", "instance_edges", "line_capture", "external_calls", "external_capture"):
            old.pop(key, None)
        payload = self.build(old)
        self.assertEqual(payload["coverage_scope"], "whole_run")
        self.assertTrue(all(node["coverage_scope"] == "whole_run" for node in payload["nodes"]))
        self.assertTrue(all(node["call_scope"] == "function" for node in payload["nodes"]))

    def test_thread_origin_fallback_preserves_start_line_and_reachability(self):
        payload = self.build()
        worker_id = next(i for i, row in enumerate(self.graph["instances"]) if row["name"] == "worker")
        self.assertEqual(self.graph["instances"][worker_id]["parent"], -1)
        worker = next(node for node in payload["nodes"] if node.get("raw_instance") == worker_id)
        edges = [edge for edge in payload["edges"] if edge["to"] == worker["id"]]
        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual(edge["provenance"], "thread_origin")
        self.assertEqual(edge["via"], "thread")
        self.assertEqual(edge["line"], self.fixture.line("thread.start()"))
        parent = next(node for node in payload["nodes"] if node["id"] == edge["from"])
        self.assertEqual(parent["name"], "main")
        self.assertTrue(worker["ex"])

    def test_legacy_none_suspension_is_normalized_without_mutating_raw_capture(self):
        dependency_path = self.fixture.root / "generator_dependency.py"
        dependency_path.write_text("def yields_none():\n    yield None\n\ndef yields_value():\n    yield 0\n")
        spec = importlib.util.spec_from_file_location("generator_dependency_fixture", str(dependency_path))
        dependency = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dependency)
        extra = '''
def project_yields_none():
    yield None

def generator_entry():
    project = project_yields_none()
    assert next(project) is None
    project.close()
    external = generator_dependency.yields_none()
    assert next(external) is None
    external.close()
    value = generator_dependency.yields_value()
    assert next(value) == 0
    value.close()
    assert project.gi_frame is None and external.gi_frame is None and value.gi_frame is None
'''
        source = self.fixture.source + extra
        self.fixture.project_file.write_text(source)
        self.fixture.project.__dict__["generator_dependency"] = dependency
        exec(compile(source, str(self.fixture.project_file), "exec"), self.fixture.project.__dict__)
        modern, lines, arcs, _ = self.fixture.run_capture(target=self.fixture.project.generator_entry)
        self.coverage = {"files": {"fixture.py": {"executed_lines": sorted(lines),
                         "executed_branches": [list(arc) for arc in sorted(arcs) if min(arc) > 0]}}}
        modern_payload = self.build(modern, entry="generator_entry")
        self.assertEqual(modern["external_capture"]["none_suspension_outcomes"], "unknown")
        modern_raw = {row["id"]: row for row in modern["external_calls"]}
        for node in modern_payload["nodes"]:
            if node.get("boundary"):
                self.assertEqual(node["boundary"]["outcomes"], modern_raw[node["boundary"]["id"]]["outcomes"])
                self.assertIsNone(node["boundary"]["outcomes_provenance"])

        # Recreate only the legacy interpretation fields on those same observed
        # events; every callable, call site, argument and count remains real.
        legacy = copy.deepcopy(modern)
        legacy["external_capture"]["schema"] = 1
        legacy["external_capture"].pop("none_suspension_outcomes")
        converted = 0
        for record in legacy["calls"] + legacy["external_calls"]:
            for sample in record.get("samples", []):
                if sample.get("status") == "unknown":
                    sample["status"] = "suspended"
                    sample["yielded"] = None if converted % 2 else {"t": "NoneType", "r": "None"}
                    sample.pop("ret_unavailable", None)
                    converted += 1
            if "outcomes" in record:
                record["outcomes"]["suspended"] += record["outcomes"].get("unknown", 0)
                record["outcomes"]["unknown"] = 0
        self.assertGreater(converted, 0)
        before = json.dumps(legacy, sort_keys=True)
        payload = self.build(legacy, entry="generator_entry")
        self.assertEqual(json.dumps(legacy, sort_keys=True), before)
        normalized = [sample for node in payload["nodes"] for sample in node["samples"]
                      if sample.get("outcome_provenance")]
        self.assertEqual(len(normalized), converted)
        zero_yields = [sample for node in payload["nodes"] for sample in node["samples"]
                       if sample.get("yielded") == {"t": "int", "r": "0"}]
        self.assertEqual(len(zero_yields), 1)
        self.assertEqual(zero_yields[0]["status"], "suspended")
        for sample in normalized:
            self.assertEqual(sample["status"], "unknown")
            self.assertNotIn("yielded", sample)
            self.assertNotIn("ret", sample)
            self.assertIn("close()", sample["ret_unavailable"])
            self.assertEqual(sample["outcome_provenance"]["raw_status"], "suspended")
        legacy_raw = {row["id"]: row for row in legacy["external_calls"]}
        aggregates = 0
        for node in payload["nodes"]:
            if not node.get("boundary"):
                continue
            raw = legacy_raw[node["boundary"]["id"]]["outcomes"]
            if raw.get("suspended"):
                aggregates += 1
                self.assertNotIn("suspended", node["boundary"]["outcomes"])
                self.assertEqual(node["boundary"]["outcomes"]["suspension_or_exception"], raw["suspended"])
                self.assertEqual(node["boundary"]["outcomes_provenance"]["raw_outcomes"], raw)
                self.assertIn("bounded samples", node["boundary"]["outcomes_note"])
        self.assertGreater(aggregates, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
