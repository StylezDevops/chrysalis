# {{title}}: agent instructions

{{description}}

## Read first

1. `initial.md` in this repo: purpose, users, constraints, risks.
2. The method: `{{framework_path}}/METHOD.md`. Read the sections for the rule IDs below. Their text lives
   there only; this file does not repeat it.
3. `docs/handover.md`: where the last session stopped.
4. `~/.claude/engineering-guardrails.md`: general code-writing guardrails.

## Rules in force

Universal:

{{universal_rules}}

Conditional, selected from `config_project.json` on {{date}}:

{{conditional_rules}}

Rerun `python "{{framework_path}}/scripts/chrysalis.py" rules --config config_project.json` after
changing the config, and update this list from its output.

## This project

- Stage: {{stage}}
- Languages: {{languages}}
- Platforms: {{platforms}}
- Remote CI: {{ci_remote}}
- Local gate: `{{local_gate}}`
- Agent cap: {{max_agents}} concurrent (U16)

## Where things are recorded

| What | Where |
|---|---|
| Work items | `docs/backlog.md` |
| Defects | `docs/register.md` (check: `chrysalis.py register check`) |
| Gates | `gates.toml` (check: `chrysalis.py gates validate`, controls: `gates run --controls`) |
| Decisions | `docs/adr/` |
| Spec, parts, checks | `.lusser/` (check: `lusser.py check`) |
| Session state | `docs/handover.md` |

## Project-specific rules

Add rules that only make sense here. Each needs a reason and, where possible, the incident it came from.
