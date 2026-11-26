#!/usr/bin/env python3
"""PreToolUse guard: `npx` may only run a tool the project already has installed.

WHY THIS EXISTS. On 2026-09-29 an agent ran `npx prettier --write` over two files in a TypeScript UI.
The project declares no formatter, so npx quietly downloaded prettier 3.9.9 from the registry and ran
it with its own defaults. It reflowed about 240 lines that nobody had touched, tsc and eslint both
stayed green, and the damage showed only in `git diff --stat`. Both files were restored from HEAD and
the edits re-applied by hand.

The formatter was the symptom. The mechanism is that `npx <name>` installs whatever `<name>` is when
the project does not have it, which also makes it a supply-chain door: a typo is a package somebody
else published.

WHAT IT REFUSES. `npx`, `npm exec`, `pnpm dlx`, `pnpm exec`, `yarn dlx` and `bunx` naming a tool that
has no entry in the project's `node_modules/.bin`. The project root is `$CLAUDE_PROJECT_DIR`, or the
current directory if that is unset. If the JS lives in a subfolder, list it in `NPX_GUARD_SUBDIRS`
(separated by `os.pathsep`, so `;` on Windows and `:` elsewhere), for example `ui;web`.

WHAT IT ALLOWS. The tools the project installs: whatever `.bin` holds. Adding a tool is a `package.json` change reviewed like any other, and then this guard lets it
through without being edited.

WHAT IT DOES NOT CATCH: a tool installed globally and run by its bare name. That does not fetch
anything, so it is not this defect.
"""

import json
import os
import pathlib
import re
import sys

TOOLS = {"Bash", "PowerShell"}

# The runner, then any flags, then the package. `npm exec -- name` and `npx --yes name` both land on
# the name; `--package=x` is refused outright because it names the package to fetch explicitly.
RUNNER = re.compile(r"(?:^|[\s;&|(])(?:npx|bunx|npm\s+exec|pnpm\s+(?:dlx|exec)|yarn\s+dlx)\b((?:\s+-{1,2}[\w-]+(?:=\S+)?)*)(?:\s+--)?\s+([@\w./:-]+)")

ROOT = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SUBDIRS = [s for s in os.environ.get("NPX_GUARD_SUBDIRS", "").split(os.pathsep) if s]
BIN_DIRS = tuple(ROOT / s / "node_modules" / ".bin" for s in SUBDIRS) + (ROOT / "node_modules" / ".bin",)

REASON = """`npx` may only run a tool this project already has installed. `{name}` is not in any
node_modules/.bin this guard checks, so npx would DOWNLOAD it and run it.

On 2026-09-29 `npx prettier --write` did exactly that: the project declared no formatter, npx fetched
prettier 3.9.9, and it reflowed about 240 untouched lines in two files while tsc and eslint stayed
green. Both files had to be restored from HEAD.

What to do instead:
- Use the tools the project already declares. If there is no formatter, match the surrounding code.
- A tool the project genuinely needs: add it to package.json, install it, and this guard lets it
  through with no edit.
- Otherwise, say which tool and why, and let the user decide."""


def installed(name: str) -> bool:
    base = name.split("@")[0] if not name.startswith("@") else name.rsplit("/", 1)[-1].split("@")[0]
    base = base.rsplit("/", 1)[-1]
    return any((d / base).exists() or (d / f"{base}.cmd").exists() for d in BIN_DIRS)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?:\n|$)", re.DOTALL)


def as_statements(command: str) -> str:
    """Heredoc bodies and quoted spans are data, not commands: a commit message that SAYS `npx x`
    was refused by the first version of this guard, which is how this function came to exist."""
    text = HEREDOC.sub("\n", command)
    out = []
    quote = ""
    for ch in text:
        if quote:
            out.append(" ")
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def offending(command: str) -> str | None:
    for match in RUNNER.finditer(as_statements(command)):
        flags, name = match.group(1) or "", match.group(2)
        if "--package" in flags or re.search(r"(?:^|\s)-p(?:\s|=|$)", flags):
            return name
        if not installed(name):
            return name
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in TOOLS:
        return 0

    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return 0

    name = offending(command)
    if name is None:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON.format(name=name),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
