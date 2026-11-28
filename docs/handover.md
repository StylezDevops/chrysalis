# Chrysalis: handover

Rewritten at the end of every session (U12). Read it first.

## The loop

1. `python scripts/chrysalis.py classify` to see the change's class and what it asks for.
2. A defect: register row, regression test shown red, fix, row CLOSED with its numbers (U3).
3. `python tests/run_all.py`, then `python tests/run_all.py --sweep`; every injection must be SEEN.
4. `python scripts/chrysalis.py gates run` and `gates run --controls`; every control red.
5. `python scripts/chrysalis.py doctor --repo . --release` passes (gate D1).
6. A part-budget change or an ambiguity resolution is written only after a human gives it.

## Where it stopped (2026-11-28)

An outside review asked for proportion, honest deferral, wider enforcement and independence from
Claude Code. All four went in (spec clauses C15 to C18, ambiguities A19 to A21, budget 36):

- `PROPORTION.md`: rule grades, change classes C0 to C2, what enforces each rule, adaptations.
- `classify`, `doctor`, `skills install`; register states SCHEDULED and ACCEPTED; `--release`.
- AGENTS.md as the generated contract, CLAUDE.md importing it, a CI workflow template.
- `hooks/check.py`, `.pre-commit-hooks.yaml`, `docs/pilot.md`.

## Open

- Gate A1 (human): the generated samples now include `docs/samples/csaw-AGENTS.md`, and
  `csaw-CLAUDE.md` changed to an import. The owner's acceptance of 2026-11-26 covered the old
  samples; it needs renewing.

## Closed this session

- R-12: `scripts/chrysalis.py` (1,341 lines) split into 14 modules by responsibility, and
  `tests/test_chrysalis.py` (768) into 3 files. `chrysalis.py check` (gate F1) now fails on any Python
  file over 500 lines; the largest is now `tests/test_governance.py`.
