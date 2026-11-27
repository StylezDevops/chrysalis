# Parts ledger: Chrysalis

Counted as added, not as planned. Documentation (README, discovery report) is not a part: nothing
executes it and no kind fits it. Tests and fixtures are checks, not parts.

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | METHOD.md | interface | the rules agents and generated files cite by ID (C1, C2, C11) | no |
| 2 | chrysalis.py: config validation and rule selection | module | C2, C3; stdlib json and a 60-line condition parser instead of a schema library | no |
| 3 | chrysalis.py: inspect, plan, apply | module | C4 to C7 | no |
| 4 | chrysalis.py: gates and register check | module | C8, C9 | no |
| 5 | chrysalis.py: worktree new, finish and sweep | module | C12; finish removes one worktree with its branch and build directory, sweep removes every merged agent branch left behind | no |
| 6 | templates/ (22 files) | interface | C7, C11; what apply writes; 7 added from the in-work project (A15) | no |
| 7 | config/ (field reference and example) | config | C3 | no |
| 8 | guardrails/engineering-guardrails.md | config | A13; copy installed when absent, drift checked by `check` | no |
| 9 | skills/chrysalis-init | handoff | the half of init that needs a person, which the tool cannot do | no |
| 10 | skills/ imported (6 skills from ~/.claude/skills) | module | A2; existing skills, scrubbed, not rewritten | no |
| 11 | hooks/ (4 hooks with tests) | module | C10; generalised from CHRYSOS and ~/.claude/hooks, plus the deferral-marker hook (A15) | no |
| 12 | fix R-1: case-sensitive asset matching | rework | found by real-input validation on the CHRYSOS copy | no |
| 13 | fix R-2: equivalents checked before existence | rework | found by real-input validation on the CHRYSOS copy | no |
| 14 | fix R-3: live .lusser files reused, not proposed | rework | found by real-input validation on the CHRYSOS and Substrate copies | no |
| 15 | fix R-4: lusser.py reads user-edited files as utf-8-sig | rework | found when a PowerShell write broke this repo's own checks.toml | no |
| 16 | fix R-5: chrysalis.py reads config, gates, register and templates as utf-8-sig | rework | same cause as R-4 | no |
| 17 | .github/workflows/ci.yml | config | C8, C10, C13; every gate except V1 and every control, on Linux and Windows; the README quick start on an empty project (A16) | no |
| 18 | hooks/git_pre_commit.py | module | C10; the deferral-marker rule as a git hook, for setups without Claude Code (A16) | no |
| 19 | fix R-6: skipped tests reported as skipped | rework | found by a fresh-clone run before CI was added | no |
| 20 | fix R-7: validate_real.py skips with exit 3 without local copies | rework | found by the same fresh-clone run | no |
| 21 | fix R-8: worktree base from --base, then repo.default_branch, then main | rework | found by an outside code review (A17) | no |
| 22 | fix R-9: one Markdown row splitter that keeps escaped and code-span pipes in their cell | rework | found by the same review | no |
| 23 | fix R-10: inspect reports every folder past the depth limit; --max-depth raises it | rework | found by the same review | no |
| 24 | fix R-11: lusser parts takes its base from --base, then repo.default_branch, then main | rework | found by checking R-8 against its siblings (U21, A18) | no |
