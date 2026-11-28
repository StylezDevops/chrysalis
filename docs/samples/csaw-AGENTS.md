# CSAW: agent instructions

An audio effect plugin ported from a Python reference.

This file is for every coding agent and every person working here, whatever tool they use. Tool-specific
files (`CLAUDE.md` and the like) import it and add only what is specific to their tool.

## Read first

1. `initial.md` in this repo: purpose, users, constraints, risks.
2. The method: `<chrysalis>/PROPORTION.md` first, then `<chrysalis>/METHOD.md` for the
   rule IDs below. Their text lives there only; this file does not repeat it.
3. `docs/handover.md`: where the last session stopped.
4. `docs/names-that-do-not-exist.md`: names agents have invented here, and the real ones.
5. `~/.claude/engineering-guardrails.md`, or your tool's equivalent: general code-writing guardrails.

## How much each change needs

Before starting a change, and again before calling it done, run:

```
python "<chrysalis>/scripts/chrysalis.py" classify --repo .
```

It prints the change's class (C0, C1 or C2), why, and what that class asks for. Work to that list.
A class may be raised by anyone and never lowered below what the diff shows.

## Rules in force

Universal:

- U1: Measure first
- U2: A check must be able to fail
- U3: A defect becomes structure
- U4: Tests argue, they do not record
- U5: Adversarial audit until a round is clean
- U6: Every fault is owned and on the record
- U7: A repeatable mistake gets a hook
- U8: One source of truth
- U9: Docs move with code
- U10: lusser, scaled to the change
- U11: Decisions carry their reasons
- U12: Sessions hand over
- U13: A report is a claim
- U14: Ask or decide
- U15: Test what changed
- U16: Parallel work is earned
- U17: Fail closed
- U18: Every unit has one outcome
- U19: Config is checked when it loads
- U20: A mechanism counts once it is shown to run
- U21: One promise, every member

Conditional, selected from `config_project.json` on 2026-11-28:

- K5 (because `risk.realtime`)
- K7 (because `ci.remote == "on-request"`)

Rerun `python "<chrysalis>/scripts/chrysalis.py" rules --config config_project.json` after
changing the config, and update this list from its output. `chrysalis.py doctor` fails while the list
and the config disagree.

## This project

- Stage: new
- Languages: c++, python
- Platforms: desktop, plugin
- Remote CI: on-request
- Local gate: `(not set: define it in gates.toml)`
- Agent cap: 2 concurrent (U16)

## Where things are recorded

| What | Where |
|---|---|
| Work items | `docs/backlog.md` |
| Defects, scheduled fixes and accepted risks | `docs/register.md` (check: `chrysalis.py register check`) |
| Gates | `gates.toml` (check: `chrysalis.py gates validate`, controls: `gates run --controls`) |
| Decisions | `docs/adr/` |
| Spec, parts, checks | `.lusser/` (check: `lusser.py check`) |
| Session state | `docs/handover.md` |
| Recurring defect patterns | `docs/bug-classes.md` |
| What has been shown to work | `docs/verification.md` |
| Fix, audit and change records | `docs/standards/` templates |
| Compliance, all of the above in 1 command | `chrysalis.py doctor --repo .` |

## Project-specific rules

Add rules that only make sense here. Each needs a reason and, where possible, the incident it came from.
