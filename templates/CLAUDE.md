# {{title}}: Claude Code instructions

@AGENTS.md

The instructions every agent follows are in `AGENTS.md`, imported above, so Claude Code reads the same
rules as any other tool. This file holds only what is specific to Claude Code.

## Hooks

The hooks in `{{framework_path}}/hooks/` refuse mistakes a machine can recognise (U7). Wire them in
`.claude/settings.json` as `{{framework_path}}/hooks/README.md` shows. Other tools call the same hooks
through `{{framework_path}}/hooks/check.py`.
