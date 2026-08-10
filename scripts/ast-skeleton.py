#!/usr/bin/env python3
"""Extract function/class/import signatures from a code file. Stdlib only.

Usage: ast-skeleton.py [file]   (reads stdin if no file given)
       ast-skeleton.py --selftest
"""
import ast
import json
import re
import sys

TS_FUNC = re.compile(r"^export\s+(?:default\s+)?(async function|function)\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
TS_DECL = re.compile(r"^export\s+(?:default\s+)?(const|class|interface|type)\s+(\w+)", re.MULTILINE)
TS_IMPORT = re.compile(r"^import\s+.*?from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
PY_DEF_RE = re.compile(r"^\s*def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
PY_CLASS_RE = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
PY_IMPORT_RE = re.compile(r"^\s*(?:import\s+(\w+)|from\s+([\w.]+)\s+import)", re.MULTILINE)


def is_python(text, filename):
    if filename and filename.endswith(".py"):
        return True
    if filename and filename.endswith((".ts", ".tsx", ".js", ".jsx")):
        return False
    return bool(re.search(r"^\s*(def |import |from \w+ import)", text, re.MULTILINE)) and not re.search(
        r"^\s*(export|import .* from|const |interface )", text, re.MULTILINE
    )


def skeleton_python(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # File mid-edit or otherwise broken — best-effort regex fallback instead of crashing.
        funcs = [f"function: {name}({args.strip()})" for name, args in PY_DEF_RE.findall(text)]
        classes = [f"class: {name}" for name in PY_CLASS_RE.findall(text)]
        deps = [a or b for a, b in PY_IMPORT_RE.findall(text)]
        return ["_(syntax error — regex fallback, best-effort)_"] + funcs + classes, deps

    exports, deps = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = ", ".join(a.arg for a in node.args.args)
            exports.append(f"function: {node.name}({args})")
        elif isinstance(node, ast.ClassDef):
            exports.append(f"class: {node.name}")
        elif isinstance(node, ast.Import):
            deps.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            deps.append(node.module)
    return exports, deps


def skeleton_json(text):
    try:
        data = json.loads(text)
    except ValueError:
        return ["(invalid json)"], []
    if not isinstance(data, dict):
        return [f"(top-level {type(data).__name__}, {len(data)} items)"], []
    deps = list(data.get("dependencies", {})) + list(data.get("devDependencies", {}))
    keys = [f"{k}: {type(v).__name__}" for k, v in data.items() if k not in ("dependencies", "devDependencies")]
    return keys, deps


def skeleton_ts(text):
    exports = []
    for kind, name, params in TS_FUNC.findall(text):
        params = re.sub(r":\s*[^,)]+", "", params).strip()  # drop type annotations
        kind = "function" if kind == "function" else "async function"
        exports.append(f"{kind}: {name}({params})" if params else f"{kind}: {name}")
    for kind, name in TS_DECL.findall(text):
        exports.append(f"{kind}: {name}")
    deps = TS_IMPORT.findall(text)
    return exports, deps


def render(filename, exports, deps):
    out = [f"## Skeleton: {filename}", "", "### Exports"]
    out += [f"- {e}" for e in exports] or ["- (none found)"]
    out += ["", "### Dependencies"]
    out += [f"- {d}" for d in deps] or ["- (none found)"]
    return "\n".join(out)


def run(text, filename):
    if filename and filename.endswith(".json"):
        exports, deps = skeleton_json(text)
    elif is_python(text, filename):
        exports, deps = skeleton_python(text)
    else:
        exports, deps = skeleton_ts(text)
    return render(filename or "<stdin>", exports, deps)


def selftest():
    py = "import os\nfrom pathlib import Path\n\ndef foo(a, b):\n    pass\n\nclass Bar:\n    pass\n"
    out = run(py, "x.py")
    assert "function: foo(a, b)" in out
    assert "class: Bar" in out
    assert "- os" in out and "- pathlib" in out

    ts = "import { useState } from 'react';\nexport function Button(a, b) {}\nexport interface Props {}\n"
    out = run(ts, "x.tsx")
    assert "function: Button(a, b)" in out
    assert "interface: Props" in out
    assert "- react" in out

    broken_py = "def foo(a, b)\n    pass\n\nclass Bar:\n    pass\n"  # missing colon -> SyntaxError
    out = run(broken_py, "broken.py")
    assert "regex fallback" in out
    assert "function: foo(a, b)" in out
    assert "class: Bar" in out

    pkg = '{"name": "x", "version": "1.0.0", "dependencies": {"react": "^18"}, "devDependencies": {"vitest": "^1"}}'
    out = run(pkg, "package.json")
    assert "- react" in out and "- vitest" in out
    assert "name: str" in out and "version: str" in out
    print("ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    filename = args[0] if args else None
    text = open(filename, encoding="utf-8").read() if filename else sys.stdin.read()
    print(run(text, filename))
