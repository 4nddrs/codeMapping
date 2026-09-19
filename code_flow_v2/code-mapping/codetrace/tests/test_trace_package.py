#!/usr/bin/env python3
"""--trace-package: follow a dependency's Python instead of stopping at its boundary.

Built from a real traced execution: a project file imports a package that lives
OUTSIDE the project root (as a venv normally does), the tracer is told to trace
inside it, and the renderer must label, source and cover its cards the same way
as project code. No fixtures are faked.
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import codetrace  # noqa: E402
import _calltree  # noqa: E402
import _mosaic  # noqa: E402

PACKAGE = '''
def outside_helper(x):
    y = x * 2
    if y > 100:
        return -1
    return y + 1
'''

PROJECT = '''
import outsidepkg

def main():
    a = outsidepkg.outside_helper(20)
    b = outsidepkg.outside_helper(70)
    return a, b
'''


class TracePackageTests(unittest.TestCase):
    def setUp(self):
        self.project_dir = tempfile.TemporaryDirectory(prefix="codetrace-trace-package-root-")
        self.package_dir = tempfile.TemporaryDirectory(prefix="codetrace-trace-package-site-")
        self.addCleanup(self.project_dir.cleanup)
        self.addCleanup(self.package_dir.cleanup)
        self.root = Path(self.project_dir.name).resolve()
        site = Path(self.package_dir.name).resolve()
        self.package = site / "outsidepkg"
        self.package.mkdir()
        (self.package / "__init__.py").write_text(textwrap.dedent(PACKAGE))
        (self.root / "fixture.py").write_text(textwrap.dedent(PROJECT))
        sys.path.insert(0, str(site))
        self.addCleanup(lambda: sys.path.remove(str(site)))
        sys.modules.pop("outsidepkg", None)
        self.addCleanup(lambda: sys.modules.pop("outsidepkg", None))
        spec = importlib.util.spec_from_file_location("trace_package_fixture", str(self.root / "fixture.py"))
        self.project = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.project)
        self.trace_packages = {"outsidepkg": str(self.package)}

    def capture(self):
        import coverage
        roots = ["fixture.py", str(self.package)]
        collector = coverage.Coverage(
            branch=True, timid=True, concurrency=["thread"], data_file=None,
            include=[str(self.root / "fixture.py"), str(self.package / "*")])
        tracer = codetrace.CallTracer(self.root, roots, HERE.parent, trace_packages=self.trace_packages)
        collector.start()
        tracer.start()
        try:
            result = self.project.main()
        finally:
            tracer.stop()
            collector.stop()
        self.assertEqual(result, (41, -1))
        path = self.root / "graph.json"
        tracer.dump(path)
        graph = json.loads(path.read_text())
        data = collector.get_data()
        cov = {"files": {}}
        for filename in data.measured_files():
            cov["files"][filename] = {
                "executed_lines": sorted(data.lines(filename) or []),
                "executed_branches": [], "missing_lines": [], "missing_branches": []}
        return graph, cov, roots

    def test_resolve_trace_packages(self):
        # a real installed package resolves to its directory, a plain module to its file
        resolved = codetrace.resolve_trace_packages(["json", "textwrap"])
        self.assertTrue(Path(resolved["json"]).is_dir())
        self.assertTrue(Path(resolved["textwrap"]).is_file())
        with self.assertRaises(ImportError):
            codetrace.resolve_trace_packages(["no_such_package_for_codetrace_tests"])
        self.assertEqual(codetrace.resolve_trace_packages([]), {})

    def test_package_label(self):
        tp = {"outsidepkg": str(self.package)}
        self.assertEqual(codetrace.package_label(str(self.package / "__init__.py"), tp),
                         "outsidepkg/__init__.py")
        self.assertEqual(codetrace.package_label(str(self.package / "sub" / "mod.py"), tp),
                         "outsidepkg/sub/mod.py")
        self.assertIsNone(codetrace.package_label(str(self.root / "fixture.py"), tp))
        # a sibling directory whose name merely starts with the package dir is not inside it
        self.assertIsNone(codetrace.package_label(str(self.package) + "2/x.py", tp))

    def test_dependency_frames_are_traced_and_labelled(self):
        graph, cov, roots = self.capture()
        self.assertEqual(graph["trace_packages"], self.trace_packages)
        names = {(c["file"], c["name"]) for c in graph["calls"]}
        self.assertIn(("outsidepkg/__init__.py", "outside_helper"), names,
                      "the dependency function is a traced call, labelled by package")
        self.assertFalse(any(".." in f or f.startswith("/") for f, _ in names),
                         "no ../../ or absolute paths leak into the trace")
        helper = next(c for c in graph["calls"] if c["name"] == "outside_helper")
        self.assertEqual(helper["count"], 2)
        edge = next(e for e in graph["edges"] if e["tname"] == "outside_helper")
        self.assertEqual(edge["tfile"], "outsidepkg/__init__.py")
        self.assertEqual(edge["cfile"], "fixture.py")
        # nothing in the traced package is recorded as an external boundary
        self.assertFalse(any((r["target"].get("name") == "outside_helper")
                             for r in graph["external_calls"]))

    def test_renderer_sources_and_covers_the_package_card(self):
        graph, cov, roots = self.capture()
        payload = _calltree.build(
            root=self.root, cg=graph, cov=cov, command="python fixture.py",
            outcome="ok", title="t", brand="b", entry="main",
            important=("outsidepkg/*.py:outside_helper",),
            trace_packages=self.trace_packages)
        cards = [n for n in payload["nodes"] if n["name"] == "outside_helper" and not n.get("boundary")]
        self.assertEqual(len(cards), 2, "one card per call site, like any project function")
        for card in cards:
            self.assertEqual(card["file"], "outsidepkg/__init__.py")
            self.assertIn("y = x * 2", card["src"], "source was read through the package location")
            self.assertTrue(card["ex"], "its executed lines are recorded, not reference-only")
            self.assertNotEqual(card["coverage_scope"], "boundary_only")
            self.assertTrue(card["important"], "important.txt patterns match the package label")
        taken = {tuple(c["ex"]) for c in cards}
        self.assertEqual(len(taken), 2, "the two call sites took different branches")
        # whole-run coverage keyed by the absolute package path was re-keyed to the label
        covered = {n["file"] for n in payload["nodes"] if n.get("mi") or n.get("ex")}
        self.assertIn("outsidepkg/__init__.py", covered)

    def test_rebuild_without_flags_uses_the_trace_own_record(self):
        # build_pages merges cg["trace_packages"] in, so a rebuild that does not
        # repeat --trace-package still resolves the labels
        graph, cov, roots = self.capture()
        payload = _calltree.build(
            root=self.root, cg=graph, cov=cov, command="python fixture.py",
            outcome="ok", title="t", brand="b", entry="main")
        cards = [n for n in payload["nodes"] if n["name"] == "outside_helper" and not n.get("boundary")]
        self.assertEqual(len(cards), 2)
        self.assertIn("y = x * 2", cards[0]["src"])

    def test_mosaic_lists_the_package_by_label(self):
        graph, cov, roots = self.capture()
        mosaic = _mosaic.build(root=self.root, roots=roots, cov=cov, command="c",
                               outcome="ok", title="t", brand="b",
                               trace_packages=self.trace_packages)
        listed = {f["path"] for f in mosaic["files"]}
        self.assertIn("outsidepkg/__init__.py", listed)
        self.assertFalse(any(".." in str(x) for x in listed))


if __name__ == "__main__":
    unittest.main()
