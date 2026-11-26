#!/usr/bin/env python3
"""PreToolUse guard: a gate register may not be piped, because a pipe eats its exit code.

WHY THIS EXISTS. A shell pipeline reports the exit status of the LAST command in it. So

    wsl -e bash tools/ci_wsl.sh 2>&1 | tail -12

exits 0 when `tail` succeeds, which it always does, and the register's own `exit 1` is thrown away.
On 2026-09-22 the Linux register failed to BUILD, the harness reported "exited with code 0", and the
work was pushed to main on the strength of it. The tree on main did not compile under clang.

Nothing was silently misreported before that, because the verdict TEXT was being read each time. But
that is the point: reading the prose and ignoring the number is a habit that works until the one run
where the prose scrolls off, and then it fails in the direction of green. The register prints a
number so that nobody has to read it.

WHAT IT REFUSES. A register or gate invocation with a `|` after it in the same command. That is:

    tools/ci_local.bat, tools/ci_wsl.sh, tools/run_gates.bat, tools/gate_*.py

WHAT TO DO INSTEAD, and the hook says this in its refusal:

    wsl -e bash tools/ci_wsl.sh > out.txt 2>&1; echo "EXIT: $?"; tail -6 out.txt

Redirect, read the code, THEN look at the text. Grepping the output FILE afterwards is untouched,
because a file is not a pipeline and reading one cannot hide a status.

WHAT IT DOES NOT CATCH, said here rather than discovered later. It stops the status being THROWN
AWAY; it cannot make anybody READ it. `ci_wsl.sh > out.txt 2>&1` with nobody looking at `$?` passes
this hook and is the same mistake one step along. It also does not see a register reached through a
variable or a wrapper script. Those are judgement, and judgement is what the hook exists to stop
relying on, so this is a partial defence and is worth knowing as one.
"""

import json
import os
import re
import sys

TOOLS = {"Bash", "PowerShell"}

# The registers and the gate scripts. `gate_*.py` is included because those print a verdict line and
# an exit code too, and `| Select-String "PASS"` on one has exactly the same hole.
# The default matches the script names of the project this was written for. Set REGISTER_PATTERN to
# a regex of your own gate scripts to reuse it, for example `(ci\.sh|run_tests\.ps1)`.
REGISTER = re.compile(
    os.environ.get("REGISTER_PATTERN")
    or r"(ci_local\.bat|ci_wsl\.(?:sh|py)|run_gates\.bat|gate_[a-z_]+\.py)",
    re.IGNORECASE,
)

REASON = """A gate register may not be piped: the pipe throws away its exit code.

A shell pipeline reports the status of the LAST command, so

    wsl -e bash tools/ci_wsl.sh 2>&1 | tail -12

exits 0 whenever `tail` succeeds, which is always. On 2026-09-22 the Linux register failed to BUILD,
the harness reported "exited with code 0", and the work went to main on the strength of it. It did
not compile under clang.

Redirect and read the number first:

    wsl -e bash tools/ci_wsl.sh > out.txt 2>&1; echo "EXIT: $?"; tail -6 out.txt

or, in PowerShell:

    & cmd /c "tools\\ci_local.bat" *> out.txt; Write-Output "EXIT: $LASTEXITCODE"

PowerShell is a slightly different case and the honest version is this: `$LASTEXITCODE` survives a
pipeline there, because it tracks the last NATIVE command rather than the pipeline. What does not
survive is the status this harness reports, which is the pipeline's. So the hazard is the same from
where you are standing even though the shell could still tell you.

Grepping the output FILE afterwards is fine and is not what this refuses. A file cannot hide a
status; a pipeline can, and does."""


# A statement ends at `;`, `&&`, `||` or a newline. Anything past one of those is a DIFFERENT
# command whose pipe has nothing to do with the register's exit code.
STATEMENT_END = re.compile(r";|&&|\|\||\n")

# ── COMMANDS THAT READ A FILE RATHER THAN RUNNING IT ─────────────────────────────────────────────
#
# THIS LIST IS THE FIX FOR A FALSE POSITIVE THAT FIRED THREE TIMES IN ONE SESSION, on
#
#     grep -n "check_hooks" tools/ci_local.bat | head -3
#
# which is a READ. The register's name appeared, a pipe followed it in the same statement, and the
# guard denied. The header already promised that "grepping the output FILE afterwards is fine"; it
# was not fine, because the name being grepped FOR was a register's.
#
# A guard that refuses correct work is one somebody routes around, and the header says so itself two
# paragraphs up. Three denials cost three round-trips and a detour into working out why, which is
# more than the guard saved on those calls.
#
# The rule is narrow on purpose: a register is INVOKED when its name is not the argument of one of
# these. Anything else -- `python`, `bash`, `wsl`, `cmd /c`, `&`, `call`, or the bare path -- is
# still treated as an invocation, so the guard fails toward denying and the incident it exists for
# stays covered.
READERS = {
    "grep", "rg", "egrep", "fgrep", "cat", "sed", "awk", "head", "tail", "less", "more",
    "ls", "dir", "find", "wc", "file", "stat", "diff", "git", "type", "cut", "sort", "uniq",
    "select-string", "get-content", "get-childitem", "get-item", "measure-object", "resolve-path",
}

# A leading `VAR=value` or a redirection is not the command. Neither is a `cd x &&`, but that ends
# the statement anyway so it never reaches here.
LEADING_NOISE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+|[<>]\S*\s+|\d?[<>]&?\d?\s+)*")


def leading_command(segment: str) -> str:
    """The first real word of a statement, lowercased and basename'd, or "" if there is not one."""
    text = LEADING_NOISE.sub("", segment.strip())
    if not text:
        return ""

    word = text.split()[0].strip("\"'&")
    word = word.replace("\\", "/").rsplit("/", 1)[-1]

    return word.lower()


def mask_quoted(command: str) -> str:
    """Blank out quoted spans, KEEPING LENGTH, so offsets into the original still line up.

    Stripping them instead was the first draft's second bug. `& python "tools\\gate_format.py" --fix
    | Select-String "x"` matches the register INSIDE the quoted path, so the remainder begins with
    that path's CLOSING quote; a strip pairs it with the next quote and eats the pipe between them.
    The call was allowed and it was the exact shape used all session.
    """
    out = []
    quote = ""

    for ch in command:
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


def offending(command: str) -> bool:
    """True when a register invocation is piped WITHIN ITS OWN STATEMENT.

    Scoped to the statement on purpose. The first draft looked for a `|` anywhere after the
    invocation, which denied the correct shape `ci_local.bat > out.txt; grep FAIL out.txt | head`
    because the pipe belonged to the grep. A guard that refuses correct work is a guard somebody
    routes around, and then it is worse than none.
    """
    masked = mask_quoted(command)

    for match in REGISTER.finditer(command):
        # The NAME is found in the original, because the path is often quoted and masking would hide
        # it. The PIPE is looked for in the masked copy, because a `|` inside an argument is not a
        # pipeline. Positions line up because masking preserves length.
        rest = masked[match.end() :]

        end = STATEMENT_END.search(rest)
        statement = rest[: end.start()] if end else rest

        if "|" not in statement:
            continue

        # ── IS THIS AN INVOCATION, OR IS THE NAME SOMEBODY'S ARGUMENT? ───────────────────────────
        #
        # Walk back to the start of the statement the match sits in and read its first word. A
        # reader there means the register is being looked AT, not run, and its exit code was never
        # in play.
        before = masked[: match.start()]
        starts = list(STATEMENT_END.finditer(before))
        segment = before[starts[-1].end() :] if starts else before

        if leading_command(segment) in READERS:
            continue

        return True

    # PROCESS SUBSTITUTION loses the status the same way and has no `|` in it at all:
    # `tail -5 <(wsl -e bash tools/ci_wsl.sh)` reports tail's code. Found by probing shapes the
    # tests did not cover, which is the only reason it is here.
    if "<(" in masked and REGISTER.search(command):
        return True

    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in TOOLS:
        return 0

    command = (payload.get("tool_input") or {}).get("command")

    if not isinstance(command, str) or not offending(command):
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }
        },
        sys.stdout,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
