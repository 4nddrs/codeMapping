"""Observed calls from project frames into dependencies, without tracing their tree.

The profiler exposes Python arguments/returns but *not* native call arguments or
results. Native records say so. Module dispatch is followed only through the
actual module wrappers until its concrete ``forward`` frame is observed.
"""
from __future__ import annotations

import ast
import dis
import inspect
import json
import linecache
import os
import re
from itertools import count


_SECRET = re.compile(r"(^|_)(password|passwd|secret|token|api_key|cookie|authorization)(_|$)", re.I)
_WRAPPERS = {"_wrapped_call_impl", "_call_impl", "__call__"}


class BoundaryRecorder:
    """Consume the same profile events as the project tracer.

    ``frame_inst`` must be the tracer's live frame-id -> instance-id dictionary.
    Call ``profile`` before removing project frames on return. Project call
    events can be sent before or after registering their instance. ``context``
    optionally receives the *project caller frame* and returns a JSON-able tag.
    Samples are bounded per boundary and context; counts include every event.
    """

    def __init__(self, root, frame_inst, is_project, summarize, summarize_locals=None,
                 max_samples=2, max_records=12000, context=None, max_contexts=12,
                 next_seq=None, exclude=None):
        self.root = str(root)
        self.frame_inst = frame_inst
        self.is_project = is_project
        self.summarize = summarize
        self.max_samples = max_samples
        self.max_records = max_records
        self.max_contexts = max_contexts
        self.context = context
        self.exclude = exclude
        self.next_seq = next_seq or count().__next__
        self.records = {}
        self._python = {}
        self._dispatch = {}
        self._native = {}
        self._code_cache = {}
        self._site_cache = {}
        self._file_cache = {}
        self._op_cache = {}
        self._module_types = {}
        self.dropped_calls = 0
        self._dropped_examples = {}
        self.context_overflow_calls = 0
        self.errors = 0
        self.excluded_calls = 0

    def _in_project(self, frame):
        return self.is_project(frame.f_code.co_filename)

    def _is_module(self, value):
        cls = type(value)
        yes = self._module_types.get(cls)
        if yes is None:
            yes = any(c.__name__ == "Module" and c.__module__ == "torch.nn.modules.module"
                      for c in cls.__mro__)
            self._module_types[cls] = yes
        return yes

    def _parsed_file(self, filename):
        if filename not in self._file_cache:
            source = "".join(linecache.getlines(filename))
            try:
                tree = ast.parse(source)
            except (SyntaxError, ValueError):
                tree = None
            calls, names = [], {}
            if tree is not None:
                def visit(node, scope=""):
                    nested = scope
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        nested = scope + ("." if scope else "") + node.name
                        if not isinstance(node, ast.ClassDef):
                            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
                            names[first] = nested
                    # Postorder is Python's ordinary nested-call evaluation order.
                    for child in ast.iter_child_nodes(node):
                        visit(child, nested)
                    if isinstance(node, ast.Call):
                        calls.append(node)
                visit(tree)
            self._file_cache[filename] = (source, calls, names)
        return self._file_cache[filename]

    def _code_info(self, code):
        info = self._code_cache.get(code)
        if info is not None:
            return info
        source, _, names = self._parsed_file(code.co_filename)
        name = getattr(code, "co_qualname", names.get(code.co_firstlineno, code.co_name))
        try:
            lines, first = inspect.getsourcelines(code)
            text = "".join(lines)
        except (OSError, IOError, TypeError):
            first, text = code.co_firstlineno, ""
        filename = code.co_filename
        # Keep package locations readable, with exact provenance separately.
        marker = "site-packages" + os.sep
        display_file = filename.split(marker, 1)[1] if marker in filename else filename
        info = {"name": name, "file": display_file, "source_path": filename,
                "first": first, "source": text, "source_available": bool(text),
                "coverage": "external source reference; internal lines were not traced"}
        self._code_cache[code] = info
        return info

    def _site(self, caller):
        key = (caller.f_code, caller.f_lasti, caller.f_lineno)
        site = self._site_cache.get(key)
        if site is not None:
            return site
        code, offset, line = key
        source, calls, _ = self._parsed_file(code.co_filename)
        expression = linecache.getline(code.co_filename, line).strip()
        matched = False
        instructions = list(dis.get_instructions(code))
        current_line = code.co_firstlineno
        same_line = []
        current_instruction = None
        for instruction in instructions:
            if instruction.starts_line is not None:
                current_line = instruction.starts_line
            if instruction.offset == offset:
                current_instruction = instruction
            if "CALL" in instruction.opname and instruction.opname != "PRECALL" and current_line == line:
                same_line.append(instruction)
        candidates = [n for n in calls if n.lineno <= line <= getattr(n, "end_lineno", n.lineno)]
        positions = getattr(current_instruction, "positions", None)
        if positions is not None and positions.col_offset is not None:
            exact = [n for n in candidates if n.lineno == positions.lineno and
                     n.col_offset == positions.col_offset and
                     getattr(n, "end_col_offset", None) == positions.end_col_offset]
            if len(exact) == 1:
                expression = ast.get_source_segment(source, exact[0]) or expression
                matched = True
        if not matched and len(candidates) == len(same_line):
            for index, instruction in enumerate(same_line):
                if instruction.offset == offset:
                    expression = ast.get_source_segment(source, candidates[index]) or expression
                    matched = True
                    break
        site = {"cline": line, "caller_bytecode_offset": offset,
                "expression": expression, "expression_exact": matched,
                "expression_note": ("source label; target identity comes from runtime profiler events"
                                    if matched else "call instruction is exact; source expression is ambiguous on this line")}
        self._site_cache[key] = site
        return site

    def _context(self, frame):
        if self.context is None:
            return None
        try:
            return self.context(frame)
        except Exception:
            return None

    def _caller_state(self, frame):
        """Preserve project comprehension/lambda calls without mapping fake cards."""
        parent = self.frame_inst.get(id(frame))
        if parent is not None:
            return {"parent": parent, "site": self._site(frame), "context": self._context(frame)}
        original, via = frame, []
        while frame is not None and len(via) < 16:
            name = frame.f_code.co_name
            if not name.startswith("<") or name == "<module>" or not self._in_project(frame):
                return None
            via.append(name)
            frame = frame.f_back
            if frame is None:
                return None
            parent = self.frame_inst.get(id(frame))
            if parent is not None:
                site = dict(self._site(original))
                source = self._code_info(frame.f_code)
                end = source["first"] + len(source["source"].splitlines()) - 1
                if (original.f_code.co_filename != frame.f_code.co_filename or
                        not source["first"] <= site["cline"] <= end):
                    site["observed_caller_line"] = site["cline"]
                    site["cline"] = frame.f_lineno
                site["synthetic_caller"] = {
                    "file": original.f_code.co_filename, "name": original.f_code.co_name,
                    "line": original.f_lineno, "bytecode_offset": original.f_lasti}
                return {"parent": parent, "site": site,
                        "context": self._context(frame), "via": via}
        return None

    def _python_target(self, frame):
        code = frame.f_code
        target = dict(self._code_info(code))
        target.update(kind="python", module=str(frame.f_globals.get("__name__", "")))
        receiver = frame.f_locals.get("self")
        cls = type(receiver) if receiver is not None else frame.f_locals.get("cls")
        if isinstance(cls, type):
            target["receiver_type"] = cls.__module__ + "." + cls.__qualname__
        target["identity"] = "%s:%s:%s" % (code.co_filename, code.co_firstlineno, target["name"])
        return target

    def _native_target(self, callable_):
        receiver = getattr(callable_, "__self__", None)
        module = getattr(callable_, "__module__", None) or ""
        name = getattr(callable_, "__qualname__", None) or getattr(callable_, "__name__", type(callable_).__name__)
        target = {"kind": "native", "module": module, "name": name,
                  "file": "[native]", "source_path": "", "first": 0, "source": "",
                  "source_available": False,
                  "coverage": "native implementation; Python profiler has no internal lines"}
        if receiver is not None and not inspect.ismodule(receiver):
            cls = type(receiver)
            target["receiver_type"] = cls.__module__ + "." + cls.__qualname__
        target["identity"] = "native:%s:%s:%s" % (module, name, target.get("receiver_type", ""))
        return target

    def _safe_summary(self, value):
        try:
            def redact(summary):
                if isinstance(summary, dict):
                    return {k: ({"t": "redacted"} if _SECRET.search(str(k)) else redact(v))
                            for k, v in summary.items()}
                if isinstance(summary, list):
                    return [redact(v) for v in summary]
                return summary
            return redact(self.summarize(value))
        except Exception:
            return {"t": type(value).__name__, "err": True}

    def _args(self, frame):
        code = frame.f_code
        n = code.co_argcount + code.co_kwonlyargcount
        if code.co_flags & inspect.CO_VARARGS:
            n += 1
        if code.co_flags & inspect.CO_VARKEYWORDS:
            n += 1
        result = {}
        for name in code.co_varnames[:n]:
            if name in frame.f_locals:
                result[name] = ({"t": "redacted"} if _SECRET.search(name)
                                else self._safe_summary(frame.f_locals[name]))
        return result

    def _start_record(self, state, target, frame=None, callable_=None):
        key = (state["parent"], state["site"]["cline"],
               state["site"]["caller_bytecode_offset"], target["identity"],
               target.get("receiver_type", ""))
        record = self.records.get(key)
        if record is None:
            if len(self.records) >= self.max_records:
                self.dropped_calls += 1
                if key in self._dropped_examples:
                    self._dropped_examples[key]["count"] += 1
                elif len(self._dropped_examples) < 20:
                    self._dropped_examples[key] = {
                        "parent": state["parent"], **state["site"],
                        "target": target["identity"], "count": 1}
                state["dropped"] = True
                return
            record = {"id": len(self.records), "parent": state["parent"],
                      **state["site"], "target": target, "count": 0,
                      "seq": self.next_seq(), "samples": [], "contexts": [],
                      "outcomes": {"returned": 0, "raised": 0, "suspended": 0, "unknown": 0},
                      "_sample_counts": {}}
            if state.get("dispatch") or state.get("via"):
                record["via"] = list(state.get("via", [])) + list(state.get("dispatch", []))
            self.records[key] = record
        record["count"] += 1
        state["record"] = record
        context = state.get("context")
        context_key = json.dumps(context, sort_keys=True, default=str)
        contexts = record["_sample_counts"]
        if context_key not in contexts:
            if len(contexts) >= self.max_contexts:
                self.context_overflow_calls += 1
                return
            contexts[context_key] = 0
            record["contexts"].append({"context": context, "count": 0})
        for item in record["contexts"]:
            if item["context"] == context:
                item["count"] += 1
                break
        if contexts[context_key] >= self.max_samples:
            return
        contexts[context_key] += 1
        sample = {"n": record["count"], "context": context, "status": "pending"}
        if frame is not None:
            sample["args"] = self._args(frame)
        else:
            sample["args_unavailable"] = "sys.setprofile c_call supplies the callable, not its argument values"
            receiver = getattr(callable_, "__self__", None)
            if receiver is not None and not inspect.ismodule(receiver):
                sample["receiver"] = self._safe_summary(receiver)
        record["samples"].append(sample)
        state["sample"] = sample

    def _return_status(self, frame, value=None):
        code = frame.f_code
        opcodes = self._op_cache.get(code)
        if opcodes is None:
            opcodes, previous = {}, ""
            for instruction in dis.get_instructions(code):
                opcodes[instruction.offset] = (instruction.opname, previous)
                previous = instruction.opname
            self._op_cache[code] = opcodes
        op, previous = opcodes.get(frame.f_lasti, ("", ""))
        if op in {"RETURN_VALUE", "RETURN_CONST"}:
            return "returned"
        if op in {"YIELD_VALUE", "YIELD_FROM"}:
            # A None profile result at a yield point also occurs when close()
            # or throw() unwinds a suspended generator, including Python 3.9.
            # It is not evidence that the generator actually yielded None.
            return "suspended" if value is not None else "unknown"
        if op == "RESUME" and previous in {"YIELD_VALUE", "YIELD_FROM"}:
            # Python 3.13 reports a yield at the following RESUME instruction.
            # A non-None value proves suspension; None can also be an exception
            # injected with generator.throw, which the profile API cannot tell.
            return "suspended" if value is not None else "unknown"
        # A Python profiler return at a non-return opcode denotes exceptional
        # frame exit. It carries None, not the exception and not a return value.
        return "raised" if op else "unknown"

    def _finish(self, state, status, arg=None, native=False):
        if state.get("finished"):
            return
        state["finished"] = True
        record = state.get("record")
        if record is None:
            return
        record["outcomes"][status] += 1
        sample = state.get("sample")
        if sample is None:
            return
        sample["status"] = status
        if status == "returned" and not native:
            sample["ret"] = self._safe_summary(arg)
        elif status == "suspended":
            sample["yielded"] = self._safe_summary(arg)
        elif status == "raised":
            sample["exception_unavailable"] = "profile event identifies exceptional exit but does not supply the exception object"
        elif native:
            sample["ret_unavailable"] = "sys.setprofile c_return supplies the callable, not the returned value"
        else:
            sample["ret_unavailable"] = "profile event could not distinguish suspension from exceptional exit; None at a generator yield point may be yield None, close(), or throw()"

    def profile(self, frame, event, arg):
        """Best-effort observation must never interrupt the target program."""
        try:
            self._profile(frame, event, arg)
        except Exception:
            self.errors += 1

    def _profile(self, frame, event, arg):
        fid = id(frame)
        if event == "return":
            state = self._python.pop(fid, None)
            dispatch = self._dispatch.pop(fid, None)
            if state is not None:
                self._finish(state, self._return_status(frame, arg), arg)
            if dispatch is not None and dispatch.get("root_frame") == fid and not dispatch.get("resolved"):
                self._start_record(dispatch, self._python_target(frame))
                sample = dispatch.get("sample")
                if sample is not None:
                    sample["args_unavailable"] = "module wrapper exited before a concrete forward frame was observed"
                self._finish(dispatch, self._return_status(frame, arg), arg)
            return
        if event in {"c_return", "c_exception"}:
            state = self._native.pop(fid, None)
            if state is not None:
                self._finish(state, "raised" if event == "c_exception" else "returned", native=True)
            return
        if event == "c_call":
            state = self._caller_state(frame)
            if state is None:
                return
            self._start_record(state, self._native_target(arg), callable_=arg)
            self._native[fid] = state
            return
        if event != "call":
            return
        caller = frame.f_back
        if caller is None:
            return
        caller_id = id(caller)
        if self.exclude is not None and self.exclude(frame.f_code.co_filename):
            if caller_id in self.frame_inst:
                self.excluded_calls += 1
            return
        dispatch = self._dispatch.get(caller_id)
        if dispatch is not None:
            receiver = frame.f_locals.get("self")
            if receiver is not None and id(receiver) == dispatch["receiver_id"]:
                if frame.f_code.co_name == "forward":
                    dispatch["resolved"] = True
                    if self._in_project(frame):
                        # The project tracer records this real project callee.
                        return
                    self._start_record(dispatch, self._python_target(frame), frame=frame)
                    self._python[fid] = dispatch
                    return
                if frame.f_code.co_name in _WRAPPERS:
                    dispatch["dispatch"].append(self._python_target(frame)["name"])
                    self._dispatch[fid] = dispatch
                    return
        if self._in_project(frame):
            return
        state = self._caller_state(caller)
        if state is None:
            return
        receiver = frame.f_locals.get("self")
        if frame.f_code.co_name in _WRAPPERS and receiver is not None and self._is_module(receiver):
            state.update(root_frame=fid, receiver_id=id(receiver),
                         dispatch=[self._python_target(frame)["name"]])
            self._dispatch[fid] = state
            return
        self._start_record(state, self._python_target(frame), frame=frame)
        self._python[fid] = state

    def dump(self):
        records = [{k: v for k, v in r.items() if not k.startswith("_")}
                   for r in self.records.values()]
        return {"external_calls": records, "external_capture": {
            "schema": 2, "none_suspension_outcomes": "unknown",
            "policy": "direct observed dependency boundaries; concrete module forward through observed dispatch wrappers",
            "max_records": self.max_records, "max_samples_per_context": self.max_samples,
            "max_contexts_per_record": self.max_contexts, "dropped_calls": self.dropped_calls,
            "dropped_examples": list(self._dropped_examples.values()),
            "context_overflow_calls": self.context_overflow_calls, "recorder_errors": self.errors,
            "excluded_instrumentation_calls": self.excluded_calls,
            "unfinished_samples": sum(s.get("status") == "pending" for r in records for s in r["samples"]),
            "limitations": [
                "Dependency bodies are source references; their internal coverage and recursive calls are not captured.",
                "Native call arguments and return values are unavailable from sys.setprofile; callable and receiver identity are observed.",
                "Python operators and descriptors without profile events cannot produce observed call arrows.",
                "Some explicit native constructors (for example dict, map, functools.partial) and native functions invoked by native protocols emit no profile call event; their absence does not prove non-execution.",
                "Python exceptional exits are identified by the final opcode; exception objects are unavailable from profile events.",
                "Generator resumes count as profile calls and yielded values are labeled suspended, not final returns.",
                "A None profile result at YIELD_VALUE, YIELD_FROM, or the following RESUME is outcome-unknown: yield None, generator.close(), and generator.throw() can produce the same event.",
                "Call expressions are source labels; ambiguous same-line expressions retain exact bytecode offsets.",
                "Project comprehension/lambda boundaries are attached to their nearest tracked project caller with an explicit synthetic-caller marker.",
                "Callbacks and process/thread dispatch require separately observed project frames; this does not trace child processes.",
            ]}}
