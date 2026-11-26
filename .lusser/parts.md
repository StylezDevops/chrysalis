# Parts ledger: Chrysalis

Counted as added, not as planned. Documentation (README, discovery report) is not a part: nothing
executes it and no kind fits it. Tests and fixtures are checks, not parts.

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | METHOD.md | interface | the rules agents and generated files cite by ID (C1, C2, C11) | no |
| 2 | chrysalis.py: config validation and rule selection | module | C2, C3; stdlib json and a 60-line condition parser instead of a schema library | no |
| 3 | chrysalis.py: inspect, plan, apply | module | C4 to C7 | no |
| 4 | chrysalis.py: gates and register check | module | C8, C9 | no |
| 5 | chrysalis.py: worktree new and finish | module | C12; closes the cleanup gap found in discovery | no |
| 6 | templates/ (15 files) | interface | C7, C11; what apply writes | no |
| 7 | config/ (field reference and example) | config | C3 | no |
| 8 | guardrails/engineering-guardrails.md | config | A13; copy installed when absent, drift checked by `check` | no |
| 9 | skills/chrysalis-init | handoff | the half of init that needs a person, which the tool cannot do | no |
| 10 | skills/ imported (6 skills from ~/.claude/skills) | module | A2; existing skills, scrubbed, not rewritten | no |
| 11 | hooks/ (3 hooks with tests) | module | C10; generalised from CHRYSOS and ~/.claude/hooks | no |
| 12 | fix R-1: case-sensitive asset matching | rework | found by real-input validation on the CHRYSOS copy | no |
| 13 | fix R-2: equivalents checked before existence | rework | found by real-input validation on the CHRYSOS copy | no |
| 14 | fix R-3: live .lusser files reused, not proposed | rework | found by real-input validation on the CHRYSOS and Substrate copies | no |
| 15 | fix R-4: lusser.py reads user-edited files as utf-8-sig | rework | found when a PowerShell write broke this repo's own checks.toml | no |
| 16 | fix R-5: chrysalis.py reads config, gates, register and templates as utf-8-sig | rework | same cause as R-4 | no |
