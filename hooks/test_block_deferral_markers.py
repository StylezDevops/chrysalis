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

# The same markers again under names the guard does not read as markers, for the cases added with
# row citations.
MK, WA = "TO" + "DO", "work" + "around"

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

BLOCK += [
    edit("src/sync.py", "a", f"x = 1  # {MK}(R12) no dash, not a row ID"),
    edit("src/sync.py", "a", f"x = 1  # {MK} see R-12 without brackets"),
    edit("src/sync.py", "a", f"# (R-12) is on this line\nx = 1  # {MK} but the marker is on the next"),
]

ALLOW = [
    edit("README.md", "a", f"{TODO} list for the docs"),
    edit("src/sync.py", f"x = 1  # {TODO}: remove", f"x = 2  # {TODO}: remove"),
    edit("src/sync.py", f"# {TODO} handle errors\nrun()", "run_with_retry()"),
    edit("src/todos.py", "a", "todo_items = load_todos()"),
    edit("src/sync.py", "a", "raise NotImplementedError('delta sync is not implemented')"),
    edit("src/sync.py", "a", f"raise NotImplementedError  # {MK}(R-12) rate limits"),
    edit("src/sync.py", "a", f"retry = 3  # {FOR_NOW}, until the provider fixes it (ISSUE-301)"),
    edit("src/sync.py", "a", f"x = 1  # {WA} ( BUG-7 )"),
    {"tool_name": "Write", "tool_input": {"file_path": str(EXISTING),
                                          "content": f"x = 1  # {TODO}: remove\ny = 2\n"}},
    {"tool_name": "Bash", "tool_input": {"command": f"echo '{TODO}' > notes.py"}},
]


def citation_cases() -> int:
    """citations() must list each cited row with its line, and nothing else."""
    text = f"a = 1\nb = 2  # {MK}(R-12)\nc = 3  # (R-99) no marker\nd = 4  # {FOR_NOW} (BUG-7)\n"
    got, want = guard.citations(text), [(2, "R-12"), (4, "BUG-7")]
    if got != want:
        print(f"citations wrong: {got} != {want}")
        return 1
    return 0


def main() -> int:
    failures = citation_cases()
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
