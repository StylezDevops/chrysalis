# Hooks

Hooks that refuse a known mistake before it lands (METHOD U7). Each one exists because of a mistake
that happened, and the docstring at the top of each file says which one, what the hook refuses and what
it does not catch. Each has a test with block cases and allow cases. They read Claude Code's PreToolUse
payload; `check.py` runs them for any other tool (below).

| Hook | Refuses | Origin |
|---|---|---|
| `block_piped_register.py` | piping a gate or CI script's output, which throws away its exit code | a red build pushed to main on a piped "exit 0" |
| `block_undeclared_npx.py` | `npx`, `npm exec`, `pnpm dlx`, `yarn dlx`, `bunx` on a tool the project has not installed | `npx prettier` downloaded a formatter and reflowed about 240 untouched lines |
| `no-heredoc-file-write.py` | writing a file with a cat/tee heredoc, and Python heredocs containing backslashes | files corrupted by halved backslashes through the Bash tool |
| `block_deferral_markers.py` | an edit that adds TODO, FIXME, HACK, "for now" or a workaround marker to a source file, unless the marker's line cites a register row such as `(R-12)` | 30 "for now" comments in the in-work project hid placeholders that reported success |

## Without Claude Code

`check.py` builds the payload from plain arguments, runs the hooks and answers with an exit code: 0
allowed, 2 refused (the reason on stderr), 1 when a hook could not answer, which is never read as an
allow. Point any agent's pre-command or post-edit hook, an editor task or a CI step at it:

```
python CHRYSALIS/hooks/check.py command "<shell command>"   # piped gate output, undeclared npx, heredoc writes
python CHRYSALIS/hooks/check.py file PATH [PATH ...]         # deferral markers added since HEAD
python CHRYSALIS/hooks/check.py staged                       # deferral markers in the staged change
python CHRYSALIS/hooks/check.py --json command "<cmd>"       # {"decision": ..., "hook": ..., "reason": ...}
```

For the [pre-commit](https://pre-commit.com) framework, add to the project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/StylezDevops/chrysalis
    rev: <a commit or tag>
    hooks:
      - id: chrysalis-deferral-markers
```

`tests/precommit_real.sh` runs it through pre-commit itself, in CI.

`git_pre_commit.py` applies the deferral-marker rule as a plain git pre-commit hook. It compares each
staged source file with HEAD and refuses the commit if uncited markers were added.
To install it in a project, put this in `.git/hooks/pre-commit` (or in a folder named by
`git config core.hooksPath`):

```sh
#!/bin/sh
exec python "CHRYSALIS/hooks/git_pre_commit.py"
```

The other 3 hooks guard shell commands an agent runs, so they have no git equivalent; `check.py command` runs them for any agent.

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
      },
      {
        "matcher": "Write|Edit|MultiEdit|mcp__serena__.*",
        "hooks": [
          {"type": "command", "command": "python \"CHRYSALIS/hooks/block_deferral_markers.py\"", "timeout": 10}
        ]
      }
    ]
  }
}
```

Each hook reads the tool call as JSON on stdin and prints a `deny` decision, or nothing. A payload it
cannot read is let through rather than blocked. That is a deliberate exception to U17: a hook that
refused every call it could not parse would stop all work, not just the mistake it targets.
