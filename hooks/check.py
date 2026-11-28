#!/usr/bin/env python3
"""Run every hook without Claude Code (METHOD U7): one entry point for any agent tool, editor or CI.

The hooks in this folder read Claude Code's PreToolUse payload. This adapter builds that payload from
plain arguments, runs the hooks, and answers with an exit code any tool can act on, so a team on
another agent platform, or none, gets the same refusals.

  python hooks/check.py command "<shell command>"   the command hooks (piped gate output, undeclared
                                                     npx, unverified installs, heredoc file writes)
  python hooks/check.py file PATH [PATH ...]         deferral markers added to each file since HEAD
  python hooks/check.py staged                       deferral markers added by the staged change

  --json   print {"decision": "allow" | "block", "hook": ..., "reason": ...} on stdout

Exit 0: allowed. Exit 2: a hook refused (the reason is on stderr). Exit 1: bad usage, or a hook that
could not run or answered with something unreadable. A hook that cannot answer never counts as an
allow (U17).

WHAT IT DOES NOT DO: wire itself into a tool. Each platform's hook or wrapper setting points at this
file; hooks/README.md shows how for Claude Code, git and the pre-commit framework.
"""

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from block_deferral_markers import SOURCE, count  # noqa: E402

COMMAND_HOOKS = ("block_piped_register.py", "block_undeclared_npx.py", "block_unverified_install.py",
                 "no-heredoc-file-write.py")


class HookError(Exception):
    pass


def run_hook(name: str, payload: dict) -> str | None:
    """The hook's refusal reason, or None if it allows. Raises HookError if it cannot answer."""
    r = subprocess.run([sys.executable, str(HERE / name)], input=json.dumps(payload), capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise HookError(f"{name} exited {r.returncode}: {r.stderr.strip()[:300]}")
    out = r.stdout.strip()
    if not out:
        return None
    try:
        decision = (json.loads(out).get("hookSpecificOutput") or {})
    except (json.JSONDecodeError, AttributeError) as e:
        raise HookError(f"{name} printed something that is not a hook answer: {e}") from e
    if decision.get("permissionDecision") == "deny":
        return decision.get("permissionDecisionReason") or f"refused by {name}"
    return None


def check_command(command: str) -> tuple[str, str] | None:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    for name in COMMAND_HOOKS:
        reason = run_hook(name, payload)
        if reason:
            return name, reason
    return None


def head_text(path: pathlib.Path) -> str:
    r = subprocess.run(["git", "-C", str(path.parent), "show", f"HEAD:./{path.name}"], capture_output=True)
    return r.stdout.decode("utf-8", errors="replace") if r.returncode == 0 else ""


def check_files(paths: list[str]) -> tuple[str, str] | None:
    for p in map(pathlib.Path, paths):
        if p.suffix.lower() not in SOURCE:
            continue
        try:
            new = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise HookError(f"cannot read {p}: {e}") from e
        before, _ = count(head_text(p.resolve()))
        after, first = count(new)
        if after > before:
            return "block_deferral_markers.py", (f"{p} adds a deferral marker ({first!r}) that cites no "
                                                 "register row (U6); cite its row, as in (R-12)")
    return None


def check_staged() -> tuple[str, str] | None:
    from git_pre_commit import staged_offences
    found = staged_offences()
    if found:
        path, marker = found[0]
        return "git_pre_commit.py", f"{path} adds a deferral marker ({marker!r}) that cites no register row (U6)"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check.py", description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="mode", required=True)
    sub.add_parser("command").add_argument("command")
    sub.add_parser("file").add_argument("paths", nargs="+")
    sub.add_parser("staged")
    args = ap.parse_args(argv)
    try:
        if args.mode == "command":
            hit = check_command(args.command)
        elif args.mode == "file":
            hit = check_files(args.paths)
        else:
            hit = check_staged()
    except (HookError, SystemExit) as e:
        print(f"check.py: a hook could not answer, so nothing is allowed: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"decision": "block" if hit else "allow", "hook": hit[0] if hit else None,
                          "reason": hit[1] if hit else None}))
    if hit:
        print(f"REFUSED by {hit[0]}:\n{hit[1]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
