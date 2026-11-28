# Chrysalis: agent instructions

This repository is the method (`METHOD.md`, `PROPORTION.md`) and its tools. It is run on its own
method; `python scripts/chrysalis.py doctor --repo . --release` must pass (gate D1).

## Read first

1. `README.md`: what is here and how each claim is checked.
2. `PROPORTION.md`, then `METHOD.md` for the rule IDs below. Their text lives there only.
3. `docs/handover.md`: where the last session stopped.
4. `.lusser/spec.md`: the clauses, the part budget and every ambiguity a human has resolved.

## How much each change needs

```
python scripts/chrysalis.py classify
```

`config_project.json` names the critical paths: `METHOD.md`, `PROPORTION.md`, `scripts/` and
`lusser.py`. A change to any of them is C2.

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

Conditional, selected from `config_project.json`:

- K2 (because `stage == "pre-release" and not risk.live_production`)

## This repository

- Standard library only, Python 3.11 or later. No dependency is added without a lusser part and a
  human's approval.
- Every gate in `gates.toml` has a control that must go red; `tests/run_all.py --sweep` arms each
  deliberate defect and needs a test naming its clause to catch it.
- A defect found here gets a row in `docs/register.md` and a regression test shown red before the fix.
- Human sign-offs (part budget, ambiguity resolutions, accepted risks) are written only after a human
  gives them.
- `tests/validate_real.py` needs local copies of the source projects and is skipped elsewhere, by name.
