#!/usr/bin/env python3
"""PreToolUse guard: an edit may not add a deferral marker to source code (METHOD U6).

WHY THIS EXISTS. The in-work project ran a register of "for now" code: 30 items, each a comment that
promised a later fix. Several hid placeholders that reported success while doing nothing: a delta sync
that only incremented its success counter, validators that returned an empty list, a connection test
hard-coded to "Connected". The rule banning the markers was prose, and some rows were closed by
rewording the comment instead of writing the code. A marker is a deferral the reader cannot see.

WHAT IT REFUSES. A Write, Edit, MultiEdit or Serena edit to a source file that leaves more deferral
markers than it found. The markers are TODO, FIXME, HACK and XXX as words, and the phrases "for now",
"temporary fix", "temporary workaround", "quick fix", "quick hack" and "workaround", in any case.
Source files are recognised by extension (see SOURCE). Markers already in the replaced text are not
counted against the edit, so touching a line near an old marker is allowed. A marker whose line cites
a register row ID in brackets, such as (R-12), is a deferral on the record and is allowed;
`chrysalis.py doctor` then fails if that row is missing or already CLOSED.

WHAT IT DOES NOT CATCH: a deferral written in other words ("will be replaced", "until X lands"), a
marker in a file type not listed, and code written by a shell command rather than an edit tool.
Nor does it judge the code: a stub that returns success with no marker at all passes. U20 covers that.
"""

import json
import pathlib
import re
import sys

# Assembled from pieces so this file does not trip a copy of itself.
WORDS = ["TO" + "DO", "FIX" + "ME", "HA" + "CK", "X" + "XX"]
PHRASES = ["for " + "now", "temporary " + "fix", "temporary " + "workaround", "quick " + "fix",
           "quick " + "hack", "work" + "around"]
MARKER = re.compile(r"\b(?:" + "|".join(WORDS) + r")\b|(?i:\b(?:" + "|".join(PHRASES) + r")\b)")
# A register row ID in brackets on the marker's line: (R-12), (BUG-7), (ISSUE-301).
CITE = re.compile(r"\(\s*([A-Z][A-Z0-9]*-\d+)\s*\)")

SOURCE = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".svelte", ".vue", ".cs", ".java", ".kt",
          ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".rb", ".php", ".sql", ".sh",
          ".ps1", ".sol", ".scala", ".dart", ".lua"}

REASON = """This edit adds a deferral marker ({marker!r}) to {path}. Under METHOD U6 a fault is fixed,
not deferred, and a marker is a deferral nobody tracks.

In the project this rule comes from, 30 "for now" comments hid placeholders that reported success
while doing nothing, and some were closed by rewording the comment rather than writing the code.

What to do instead:
- Write the real implementation now.
- If it cannot be written yet, make the placeholder throw, so a caller cannot mistake it for working
  code (U20), open a register row for it, and cite the row on the marker's line: {marker}(R-12).
- If it is to be fixed later or left on purpose, the row says so (SCHEDULED or ACCEPTED, U6), and
  only a human records that decision."""


def count(text: str) -> tuple[int, str | None]:
    """Markers that cite no register row, and the first of them. A marker whose line also carries a
    row ID in brackets, such as (R-12), is on the record and is not counted (U6)."""
    found = [m for line in (text or "").splitlines() if not CITE.search(line)
             for m in MARKER.findall(line)]
    return len(found), (found[0] if found else None)


def citations(text: str) -> list[tuple[int, str]]:
    """(line number, row ID) for every marker that cites a row; doctor checks each ID is live."""
    return [(n, cid) for n, line in enumerate((text or "").splitlines(), 1) if MARKER.search(line)
            for cid in CITE.findall(line)]


def offending(payload: dict) -> str | None:
    """The first marker an edit adds to a source file, or None."""
    tool = payload.get("tool_name") or ""
    args = payload.get("tool_input") or {}
    path = args.get("file_path") or args.get("relative_path") or ""
    if pathlib.Path(path).suffix.lower() not in SOURCE:
        return None
    pairs = []  # (text replaced, text written)
    if tool == "Write":
        old = ""
        try:
            old = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        pairs.append((old, args.get("content")))
    elif tool == "Edit":
        pairs.append((args.get("old_string"), args.get("new_string")))
    elif tool == "MultiEdit":
        pairs += [(e.get("old_string"), e.get("new_string")) for e in args.get("edits") or []]
    elif tool.startswith("mcp__serena__"):
        pairs.append((args.get("needle"), args.get("repl") or args.get("body")))
    else:
        return None
    for old, new in pairs:
        if not isinstance(new, str):
            continue
        before, _ = count(old if isinstance(old, str) else "")
        after, first = count(new)
        if after > before:
            return first
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    marker = offending(payload)
    if marker is None:
        return 0
    args = payload.get("tool_input") or {}
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON.format(
                    marker=marker, path=args.get("file_path") or args.get("relative_path")),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
