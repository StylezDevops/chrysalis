r"""PreToolUse/Bash guard: refuse two heredoc patterns that keep failing through the Bash tool.

1. Creating a file with a cat/tee heredoc. Writing a file as `cat > path <<'EOF' ... EOF` keeps
   breaking on quoting -- the outer command fails to parse ("unexpected EOF while looking for matching
   quote"), the file is not written, and the whole attempt is paid for twice. The Write tool does the
   same job in one call with no quoting layer at all.

2. An inline Python heredoc whose body contains a backslash. Through the Bash tool the backslashes in
   a `python - <<'PY'` body arrive halved: `"\\x00"` reaches Python as `"\x00"` and writes a real NUL
   byte, `'\\s'` becomes `'\s'`. It has corrupted source files and data files more than once. Put the
   script in a file with the Write tool and run that file instead.

Deliberately NOT blocked, because these are reliable and useful:
  python - <<'PY' ... PY          (inline script with no backslash in it)
  git commit -F - <<'MSG' ... MSG (stdin to a command)
  anything > file                 (ordinary redirect, no heredoc)
"""
import json
import re
import sys

# `cat` has to both redirect to a file AND take a heredoc, in either order; `tee` needs only the
# heredoc, because writing a file is all tee does. The [^;&|] guards stop a match spanning two
# chained commands.
FILE_WRITE = re.compile(
    r"\bcat\b[^;&|]*(?:>[^;&|]*<<|<<[^;&|]*>)"
    r"|\btee\b[^;&|]*<<"
    r"|<<[^;&|]*\btee\b"
)

# A python interpreter (python, python3, py, python.exe, a venv path ending in one) reading a heredoc on
# the same line. The heredoc body is everything after that line, up to the closing marker.
PY_HEREDOC = re.compile(r"(?:^|[\s/\\;&|(])(?:python[0-9.]*|py)(?:\.exe)?\b[^\n]*<<-?\s*['\"]?(\w+)['\"]?")

FILE_WRITE_REASON = (
    "Blocked: writing a file with a cat/tee heredoc. This quoting pattern fails through the Bash "
    "tool (the outer command breaks on the nested quotes and the file is never written). Use the "
    "Write tool for new file content, or Edit for a change to an existing file. A heredoc piped to "
    "a command's stdin (python - <<'PY', git commit -F -) is fine and is not blocked."
)

PY_BACKSLASH_REASON = (
    "Blocked: an inline Python heredoc containing a backslash. Through the Bash tool those backslashes "
    "arrive halved (a doubled backslash before x00 becomes a real NUL byte), which has corrupted files. "
    "Write the script to a file with the Write tool (the scratchpad is fine) and run that file, or make "
    "the edit with Edit / Serena. A heredoc script with no backslash in it is not blocked."
)


def _python_heredoc_has_backslash(command: str) -> bool:
    for m in PY_HEREDOC.finditer(command):
        marker = m.group(1)
        body_start = command.find("\n", m.end())
        if body_start < 0:
            continue
        rest = command[body_start + 1:]
        end = re.search(rf"^\s*{re.escape(marker)}\s*$", rest, re.MULTILINE)
        body = rest[: end.start()] if end else rest
        if "\\" in body:
            return True
    return False


def _deny(reason: str) -> None:
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                "permissionDecisionReason": reason}},
        sys.stdout,
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # not our business: never block on a payload we cannot read
    command = (payload.get("tool_input") or {}).get("command") or ""
    if FILE_WRITE.search(command):
        _deny(FILE_WRITE_REASON)
    elif _python_heredoc_has_backslash(command):
        _deny(PY_BACKSLASH_REASON)


if __name__ == "__main__":
    main()
