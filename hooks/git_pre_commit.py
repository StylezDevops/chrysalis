#!/usr/bin/env python3
"""git pre-commit hook: a commit may not add a deferral marker to source code (METHOD U6).

The same rule as block_deferral_markers.py, for people and tools that do not use Claude Code. It
compares each staged source file with its version at HEAD and refuses the commit when the staged
version holds more markers than HEAD did, so an old marker the commit does not add is not held
against it.

Install in a project (from its root):

  git config core.hooksPath .githooks          # once, then put a .githooks/pre-commit that runs:
  python CHRYSALIS/hooks/git_pre_commit.py

or copy a one-line shell script calling it into .git/hooks/pre-commit.

WHAT IT DOES NOT CATCH: the same gaps as block_deferral_markers.py, and a commit made with
--no-verify, which skips every git hook.
"""

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from block_deferral_markers import SOURCE, count  # noqa: E402


def git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True)


def staged_offences(cwd: str | None = None) -> list[tuple[str, str]]:
    """(path, first added marker) for every staged source file that adds markers."""
    names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", cwd=cwd)
    if names.returncode:
        raise SystemExit(f"git diff failed: {names.stderr.decode(errors='replace')}")
    found = []
    for path in filter(None, names.stdout.decode("utf-8", errors="replace").split("\0")):
        if pathlib.Path(path).suffix.lower() not in SOURCE:
            continue
        new = git("show", f":{path}", cwd=cwd).stdout.decode("utf-8", errors="replace")
        head = git("show", f"HEAD:{path}", cwd=cwd)
        old = head.stdout.decode("utf-8", errors="replace") if head.returncode == 0 else ""
        before, _ = count(old)
        after, first = count(new)
        if after > before:
            found.append((path, first))
    return found


def main() -> int:
    offences = staged_offences()
    if not offences:
        return 0
    print("Commit refused: it adds deferral markers to source code (METHOD U6).", file=sys.stderr)
    for path, marker in offences:
        print(f"  {path}: {marker!r}", file=sys.stderr)
    print("Write the real implementation, or make the placeholder throw and record the open item in "
          "the register or handover.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
