"""Drive the heredoc guard end to end: JSON in on stdin, decision out on stdout.

Run it with:  python hooks/test_no_heredoc_file_write.py
"""

import json
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).resolve().parent / "no-heredoc-file-write.py"
BS = chr(92)  # a backslash, built so this file has none in its test strings

BLOCK = [
    "cat > notes.txt <<'EOF'\nhello\nEOF",
    "cat <<'EOF' > notes.txt\nhello\nEOF",
    "tee notes.txt <<'EOF'\nhello\nEOF",
    f"python - <<'PY'\nprint('a{BS}{BS}x00b')\nPY",
]

ALLOW = [
    "python - <<'PY'\nprint('no backslash here')\nPY",
    "git commit -F - <<'MSG'\nsubject line\nMSG",
    "echo hello > notes.txt",
    "cat notes.txt",
]


def decision(command: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                         text=True, check=True).stdout
    if not out.strip():
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def main() -> int:
    failures = 0

    for command in BLOCK:
        if decision(command) != "deny":
            print(f"NOT BLOCKED (should be): {command!r}")
            failures += 1

    for command in ALLOW:
        if decision(command) != "allow":
            print(f"BLOCKED (should not be): {command!r}")
            failures += 1

    print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {failures} wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
