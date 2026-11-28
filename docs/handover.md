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
Claude Code. All four went in (spec clauses C15 to C18, ambiguities A19 to A23, budget 47):

- `PROPORTION.md`: rule grades, change classes C0 to C2, what enforces each rule, adaptations.
- `classify`, `doctor`, `skills install`; register states SCHEDULED and ACCEPTED; `--release`.
- AGENTS.md as the generated contract, CLAUDE.md importing it, a CI workflow template.
- `hooks/check.py`, `.pre-commit-hooks.yaml`, `docs/pilot.md`.

## Open

- Nothing. Gate A1 was renewed by the owner on 2026-11-28 for the new samples (`csaw-AGENTS.md`,
  and `csaw-CLAUDE.md` as an import).

## Closed this session

- R-12: `scripts/chrysalis.py` (1,341 lines) split into 14 modules by responsibility, and
  `tests/test_chrysalis.py` (768) into 3 files. `chrysalis.py check` (gate F1) now fails on any Python
  file over 500 lines; the largest is now `tests/test_governance.py`.
- R-13: `gates run --controls` counted any non-zero exit as a control going red. Every automated
  gate now declares `control_expect`, the finding its own detector prints for the planted defect, and
  a control counts only when it fails and its output matches.
- R-14 to R-18 from a source-level review: worktree finish refuses a build folder inside the repo,
  worktree or git directory; gate ids required and file-name safe; `--only` must select real automated
  gates; apply refuses any target that resolves outside the repo; sensitive risk flags need
  `change.critical_paths`, and doctor fails a stale entry.
- The same review: the generated workflow follows `ci.remote` and runs the project's gates and
  controls; generated files say `${CHRYSALIS_HOME}`, which the gate runner sets and expands; the
  framework pin is a full commit or apply refuses; every action is pinned to a SHA.
- `hooks/block_unverified_install.py`: an install of a package no manifest declares needs a
  human-approved entry in `docs/dependencies.md`.

## How changes land now

`main` requires the 5 CI checks. Push work to a branch, let CI pass on it, then merge or fast-forward
`main` to that commit; a direct push of an unchecked commit to `main` is refused.
