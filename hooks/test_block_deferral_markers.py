"""Drive the deferral-marker guard over its block and allow cases.

Run it with:  python hooks/test_block_deferral_markers.py

Markers are assembled from pieces so this file's own edits are not refused by the guard it tests.
"""

import importlib.util
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "block_deferral_markers.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

TODO, FOR_NOW, WORKAROUND = "TO" + "DO", "for " + "now", "work" + "around"

_tmp = tempfile.TemporaryDirectory()
EXISTING = pathlib.Path(_tmp.name) / "old.py"
EXISTING.write_text(f"x = 1  # {TODO}: remove\n", encoding="utf-8")


def edit(path, old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old, "new_string": new}}


BLOCK = [
    edit("src/sync.py", "return run()", f"return 0  # {TODO} implement"),
    edit("src/Sync.cs", "Run();", f"// {FOR_NOW.title()}, we'll create a basic implementation\nRun();"),
    edit("app/x.ts", "a()", f"a() // {WORKAROUND} for the API"),
    {"tool_name": "Write", "tool_input": {"file_path": str(pathlib.Path(_tmp.name) / "new.go"),
                                          "content": f"// FIX{'ME'} later\npackage x\n"}},
    {"tool_name": "MultiEdit", "tool_input": {"file_path": "lib/a.rb", "edits": [
        {"old_string": "a", "new_string": "b"},
        {"old_string": "c", "new_string": f"c # HA{'CK'}"}]}},
    {"tool_name": "mcp__serena__replace_content",
     "tool_input": {"relative_path": "scripts/tool.py", "needle": "pass", "repl": f"pass  # {FOR_NOW}"}},
    {"tool_name": "Write", "tool_input": {"file_path": str(EXISTING),
                                          "content": f"x = 1  # {TODO}: remove\ny = 2  # {TODO}\n"}},
]

ALLOW = [
    edit("README.md", "a", f"{TODO} list for the docs"),
    edit("src/sync.py", f"x = 1  # {TODO}: remove", f"x = 2  # {TODO}: remove"),
    edit("src/sync.py", f"# {TODO} handle errors\nrun()", "run_with_retry()"),
    edit("src/todos.py", "a", "todo_items = load_todos()"),
    edit("src/sync.py", "a", "raise NotImplementedError('delta sync is not implemented')"),
    {"tool_name": "Write", "tool_input": {"file_path": str(EXISTING),
                                          "content": f"x = 1  # {TODO}: remove\ny = 2\n"}},
    {"tool_name": "Bash", "tool_input": {"command": f"echo '{TODO}' > notes.py"}},
]


def main() -> int:
    failures = 0
    for payload in BLOCK:
        if guard.offending(payload) is None:
            print(f"NOT BLOCKED (should be): {payload}")
            failures += 1
    for payload in ALLOW:
        if guard.offending(payload) is not None:
            print(f"BLOCKED (should not be): {payload} -> {guard.offending(payload)}")
            failures += 1
    print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {failures} wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
