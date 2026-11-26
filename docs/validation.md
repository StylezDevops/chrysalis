# Validation against real repositories

Measured 2026-11-26 09:44 by `python tests/validate_real.py`. Regenerated on every run; do not edit by hand.

Method: each repository was copied with `git clone --depth 1` into a temp folder (tracked files only,
so ignored and secret files never left the source). Every file was hashed before and after
`chrysalis.py apply`, and the git state (HEAD, branches, remotes, staged files, commit count) was
compared. The sources were only read.

## Existing repositories

| Target | Files before | Changed | Deleted | Created | CREATE | PROPOSE | REUSE | Git state same | Only untracked additions | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| CHRYSOS | 1858 | 0 | 0 | 8 | 5 | 1 | 8 | True | True | PASS |
| SUBSTRATE | 3569 | 0 | 0 | 13 | 10 | 0 | 4 | True | True | PASS |
| MIDAS | 166 | 0 | 0 | 15 | 12 | 0 | 1 | True | True | PASS |
| CSAW_REPO | 63 | 0 | 0 | 16 | 12 | 1 | 0 | True | True | PASS |

What apply reused instead of duplicating, and what it only proposed:

- **CHRYSOS**: reused docs/backlog.md -> docs/BACKLOG.md, docs/register.md -> docs/AUDIT_REGISTER.md, docs/handover.md -> docs/HANDOVER-2026-10-19.md (+2 more), docs/adr/ADR-000-template.md -> decisions/ADR-001-port-from-reference.md (+183 more), gates.toml -> VERIFICATION.md (+2 more), .lusser/spec.md -> .lusser/spec.md, .lusser/parts.md -> .lusser/parts.md, .lusser/checks.toml -> .lusser/checks.toml; proposed CLAUDE.md.
- **SUBSTRATE**: reused gates.toml -> .githooks/pre-push (+1 more), .lusser/spec.md -> .lusser/spec.md, .lusser/parts.md -> .lusser/parts.md, .lusser/checks.toml -> .lusser/checks.toml; proposed nothing.
- **MIDAS**: reused gates.toml -> tools/ci_local.bat (+1 more); proposed nothing.
- **CSAW_REPO**: reused nothing; proposed CLAUDE.md.

## New project

An empty folder holding only the CSAW brief and its Python reference.

| Check | Result |
|---|---|
| apply exit code | 0 |
| brief and reference unchanged | True |
| initial.md created | True |
| docs/backlog.md created | True |
| gates.toml created | True |
| CLAUDE.md created | True |
| rule IDs cited in CLAUDE.md | K5, K7, U1, U2, U3, U4, U5, U6, U7, U8, U9, U10, U11, U12, U13, U14, U15, U16 |
| METHOD sentences copied into CLAUDE.md | 0 |
| generated gates.toml validates (exit) | 0 |
| files created | 16 |
| verdict | PASS |

## Limits

- A shallow clone copies tracked files only. Untracked or ignored files in the source (for example a
  gitignored register) were not present, so equivalents that exist only as ignored files were not tested.
- The configs used here were written by the harness, not by a human. They are in tests/validate_real.py.
