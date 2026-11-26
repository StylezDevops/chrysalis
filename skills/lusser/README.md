# lusser

A skill and a 300-line checker that apply Lusser's product law to AI-built software:
hold the part count down, resolve spec ambiguity with a human first, and cover every
clause with a check that fails differently from an agent.

## Layout

```
lusser/
├── SKILL.md                    the discipline (read by the agent)
├── scripts/lusser.py           init | parts --base <ref> | check   (Python 3.11+, stdlib only)
├── references/
│   ├── formats.md              exact shapes of spec.md, parts.md, checks.toml, escapes.md
│   └── check-kinds.md          how to produce each check kind in C++, C#, TS, Python
└── examples/{cpp,typescript,python}/   filled-in .lusser/ directories
```

## Use

```
python scripts/lusser.py init             # creates .lusser/ in the repo root
# ... agent drafts spec.md, human resolves ambiguities, budget agreed ...
python scripts/lusser.py parts --base main # draft ledger rows from the diff
python scripts/lusser.py check             # exit 1 on any rule violation
```

## Claude Code hook (optional)

Claude Code hooks receive a JSON payload on stdin (`tool_name`, `tool_input`, …); there is no
env var carrying the tool input. Run the check before a `git push` rather than every commit,
so it does not fight small green commits. `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{ "type": "command",
        "command": "python3 -c \"import json,sys,subprocess; d=json.load(sys.stdin); sys.exit(0) if 'git push' not in d.get('tool_input',{}).get('command','') else sys.exit(2 if subprocess.call(['python3','.claude/skills/lusser/scripts/lusser.py','check']) else 0)\"" }]
    }]
  }
}
```

Exit 2 from a PreToolUse hook blocks the tool call. Simpler and just as good: add
`python3 scripts/lusser.py check` as a CI step and skip the hook entirely.

## What it will not do

It cannot verify that a `human-accept` line is real, that a `spec-test` was written before
the code, or that the parts list is complete. Those are on the human. The checker's job is to
make the omissions visible, not impossible.
