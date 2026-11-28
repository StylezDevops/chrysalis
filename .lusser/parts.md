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
| 25 | scripts/proportion.py: grade table, change classes, adaptations | module | C15; one source for grades, read from PROPORTION.md (A19) | no |
| 26 | chrysalis.py classify | interface | C15; the class of a diff, its reasons and its obligations; refuses a lowered class (A19, A20) | no |
| 27 | config keys change.critical_paths, change.small_lines, adapt, markers.exempt | config | C15, C17; each validated at load and tested for its effect (U19) | no |
| 28 | register states SCHEDULED and ACCEPTED, dated, and --release | rework | C16; a recorded deferral instead of an absolute ban (A19) | no |
| 29 | deferral hook: a marker citing a register row is allowed | rework | C16; markers on the record, checked by doctor | no |
| 30 | chrysalis.py doctor | interface | C17; read-only compliance in 1 command (A19) | no |
| 31 | templates/ci-chrysalis.yml and gate D1 | config | C17; doctor and classify in a project's CI, pinned to a framework commit; this repo passes its own doctor | no |
| 32 | AGENTS.md template, CLAUDE.md importing it | rework | C18; an agent-neutral contract (A19) | no |
| 33 | hooks/check.py | module | C18; every hook callable without Claude Code | no |
| 34 | .pre-commit-hooks.yaml | config | C18; the deferral hook for the pre-commit framework, run for real by tests/precommit_real.sh | no |
| 35 | chrysalis.py skills install | interface | C18; never overwrites a different skill; --prefix installs beside it | no |
| 36 | fix R-12: chrysalis.py split into 14 modules by responsibility, spec tests into 3 files, and a line limit in check | rework | found while acting on the 2026-11-28 review (A21) | no |
| 37 | fix R-13: a control counts as red only with the gate's own finding (control_expect) | rework | found by the outside review's second look (A22) | no |
| 38 | fix R-14: worktree finish refuses a build folder inside the repo, worktree or git directory | rework | found by the source-level review (A23) | no |
| 39 | fix R-15: gate ids required and safe in a file name | rework | same review | no |
| 40 | fix R-16: --only must select real automated gates | rework | same review | no |
| 41 | fix R-17: apply refuses a target that resolves outside the repo | rework | same review | no |
| 42 | fix R-18: sensitive risk flags need critical paths; doctor fails a stale path | rework | same review | no |
| 43 | generated workflow follows ci.remote and runs the project's gates and controls | rework | same review | no |
| 44 | ${CHRYSALIS_HOME} in generated files, set and expanded by the gate runner | rework | same review; no machine path leaves this checkout | no |
| 45 | framework.ref: the pin is a full commit or apply refuses | config | same review; no fallback to a moving branch | no |
| 46 | every GitHub Action pinned to a commit SHA | config | same review | no |
| 47 | hooks/block_unverified_install.py and the docs/dependencies.md template | module | the supply-chain check enforced, not only advised (A23) | no |
| 48 | fix R-19: a gate that hangs times out as its own failure, keeps its output, and the run goes on | rework | found by review (A24) | no |
| 49 | fix R-20: a symlink given as the build folder is refused | rework | same review | no |
| 50 | fix R-21: the install guard reads nested shells and refuses an encoded command | rework | same review | no |
| 51 | fix R-22: manifests read by format-aware parsers, dependency sections only | rework | same review | no |
| 52 | fix R-24: a register test path outside the repo does not count | rework | found by the boundary tests | no |
| 53 | fix R-25: a gates file of the wrong shape is refused, not crashed on | rework | found by the boundary tests | no |
| 54 | fix R-26: worktree finish resumes an interrupted cleanup | rework | found by the boundary review | no |
| 55 | schema_version, four problem kinds, migrations and deprecations | schema-change | C19 (A24) | no |
| 56 | chrysalis.py config migrate | interface | C19 | no |
| 57 | chrysalis.py risk | interface | risk coverage for audit (A24) | no |
| 58 | PACKS.md (K11, K12) and infrastructure files classified C2 | module | C20 | no |
| 59 | tests/infra_sim.py, its fixtures, gate I1 and its CI job | module | C20; real-input simulation in Docker | no |
| 60 | infra-change record template, infrastructure and stack gate examples | rework | C20 | no |
| 61 | workflow permissions as a tested invariant, actionlint on both workflows | config | review (A24) | no |
| 62 | config key risk.infrastructure | config | C20; selects K11 | no |
