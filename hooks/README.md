# Hooks

Claude Code PreToolUse hooks (METHOD U7). Each one exists because of a mistake that happened, and the
docstring at the top of each file says which one, what the hook refuses and what it does not catch.
Each has a test with block cases and allow cases.

| Hook | Refuses | Origin |
|---|---|---|
| `block_piped_register.py` | piping a gate or CI script's output, which throws away its exit code | a red build pushed to main on a piped "exit 0" |
| `block_undeclared_npx.py` | `npx`, `npm exec`, `pnpm dlx`, `yarn dlx`, `bunx` on a tool the project has not installed | `npx prettier` downloaded a formatter and reflowed about 240 untouched lines |
| `no-heredoc-file-write.py` | writing a file with a cat/tee heredoc, and Python heredocs containing backslashes | files corrupted by halved backslashes through the Bash tool |

Run the tests:

```
python tests/run_all.py --only hooks
```

## Settings

`block_piped_register.py` matches `ci_local.bat`, `ci_wsl.sh`, `run_gates.bat` and `gate_*.py` by
default. Set `REGISTER_PATTERN` to a regex of your own gate scripts. `block_undeclared_npx.py` looks in
`$CLAUDE_PROJECT_DIR/node_modules/.bin`; list sub-packages in `NPX_GUARD_SUBDIRS` (separated by `;` on
Windows, `:` elsewhere).

## Installing

Chrysalis never edits `.claude/settings.json` for you. Add this to the project's `.claude/settings.json`
(or `~/.claude/settings.json` for every project), replacing `CHRYSALIS` with the repo path:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {"type": "command", "command": "python \"CHRYSALIS/hooks/block_piped_register.py\"", "timeout": 10},
          {"type": "command", "command": "python \"CHRYSALIS/hooks/block_undeclared_npx.py\"", "timeout": 10},
          {"type": "command", "command": "python \"CHRYSALIS/hooks/no-heredoc-file-write.py\"", "timeout": 10}
        ]
      }
    ]
  }
}
```

Each hook reads the tool call as JSON on stdin and prints a `deny` decision, or nothing. A payload it
cannot read is let through rather than blocked.
