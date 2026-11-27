# Discovery report

Date: 2026-11-25. Read-only investigation. Nothing in any source project was changed.

## Scope

| Project | Kind | History | Evidence read |
|---|---|---|---|
| In-work project | the source of a large share of the original rules and methodology; not named here | | |
| Client web projects | evidence read under their own change-control rules, not listed here | | |
| Substrate | owned web3 product (FastAPI, SvelteKit, Solidity) | 1047 commits, 2026-06-13 to now | CLAUDE.md, .lusser, register, pre-push, 81 memories |
| MIDAS | owned audio plugin (C++/JUCE) | 2026-07-02 to 2026-09-11 | CLAUDE.md, VERIFICATION.md, BUG_CLASSES.md, 81 memories |
| CHRYSOS | owned audio plugin (C++/JUCE) | 1030 commits, 2026-09-10 to now | CLAUDE.md, AGENTS.md, VERIFICATION.md, 184 ADRs, hooks, 98 memories |
| Global | ~/.claude | n/a | CLAUDE.md, engineering-guardrails.md, skills, hooks |

Two subagents read the source projects. 9 of their claims were checked against the files and all held.

## The method, as it evolved

INFERRED from dates. The same method gets stricter with each project. A large share of the original
rules and methodology came from an in-work project that this report does not name; the projects below
carried that material forward and added to it.

1. **Client web work (from April):** written rules arrive: a test pyramid, a threat model for each feature, attack scenarios that must fail, performance budgets, conventional commits.
2. **MIDAS (July):** "measure before reasoning" becomes a hard rule. Numbered gates. A bug-class catalogue (`docs/BUG_CLASSES.md`, C1 to about C81).
3. **CHRYSOS (September):** adds PreToolUse hooks born from incidents, ADRs, the defect register, the S0 sabotage gate that proves every gate can fail, gate parity checks and lusser.
4. **Substrate (same period):** carry the loop across as the `register-loop` skill. They add a docs-currency gate, a fail-closed pre-push path matrix, and blast-radius classes for live systems.

## Universal rules (found in several projects)

| # | Rule | Evidence |
|---|---|---|
| U1 | **Measure first.** Reproduce the defect as a number through the shipping path, prove the detector sees it, localise, change one thing, re-measure. A change that makes no difference falsifies the guess. | MIDAS CLAUDE.md; CHRYSOS CLAUDE.md; Substrate register-loop.md |
| U2 | **A check must be able to fail.** Positive control, sabotage injection or revert-the-fix before trusting a green. "A gate that has never failed is not a gate, it is decoration." | CHRYSOS VERIFICATION.md:124 and S0; Substrate storage-layout self-test |
| U3 | **A defect becomes structure.** Register row with a measured number, a regression test red before the fix, a new gate if it is a new class, then a rule, ADR or lesson. | CHRYSOS AUDIT_REGISTER and AGENTS.md PR checklist; Substrate R-103; MIDAS BUG_CLASSES.md |
| U4 | **Tests argue, they do not record.** Sweep rather than pin. Prefer property assertions. Never derive the expected value from the code under test. Assert the swept variable varied. | MIDAS gate-coverage doctrine; Substrate test-quality-lesson; CHRYSOS a-gate-green-where-the-defect-cannot-appear |
| U5 | **Adversarial audit until clean.** A fresh-context auditor reviews the fix as well as the defect. Rounds are sized to risk. An audit that finds only low-severity issues is not clean. | register-loop skill; Substrate never-accept-faults; CHRYSOS register-loop.md |
| U6 | **A mistake of recognisable shape gets a hook.** Each hook records the incident behind it, what it does not catch, and its own positive control. | CHRYSOS .claude/hooks and H10; CHRYSOS trust-the-number-not-the-prose |
| U7 | **One source of truth, or a mechanical diff.** | CHRYSOS check_gate_parity.py; Substrate docs-map.json and test_api_reference_complete.py |
| U8 | **Docs move with code.** Reversals are struck through, not deleted. | Substrate check-docs-current.mjs; CHRYSOS CLAUDE.md |
| U9 | **Fix, never defer.** A problem seen is owned, pre-existing or not. Only the project owner can leave a fault in place. | Substrate fix-never-defer, never-accept-faults; CHRYSOS a-problem-seen-is-owned; global guardrails section 4 |
| U10 | **lusser.** Numbered clauses, ambiguities resolved by a human, a part budget, and check kinds that fail differently from an agent. | .lusser/ in CHRYSOS and Substrate |
| U11 | **Decisions carry their reasons.** Rejected alternatives, measurements and a revisit condition. | CHRYSOS decisions/; Substrate dated inline decisions |
| U12 | **Sessions hand over.** Write the handover at about 85% context. Start and close rituals. | register-loop skill; CHRYSOS HANDOVER-*.md |
| U13 | **A report is a claim.** Read the diff, not the summary. Read the exit code, not the prose. Keep verification and an irreversible action out of the same command. | CHRYSOS the-worktree-agent-brief, block_piped_register, block_coupled_push |

## Conditional rules

| Rule | Applies when | Evidence |
|---|---|---|
| Blast-radius classes R0 to R4, one approval per live change, rollback rehearsed before it counts | a live production system exists | client project C change-control.md; client project B "never iterate live" |
| No compatibility code; the rule expires at first release | pre-release, no users | Substrate principle-pre-release-no-legacy.md |
| Migrations idempotent, reversible and tested on a copy of production data | live data exists | client project B CLAUDE.md "Backwards compatibility" |
| Threat model per feature, attack E2E tests | money, personal data or auth | Substrate CLAUDE.md section 14 |
| Performance budget that fails the build | user-facing web, real-time audio | CHRYSOS G6, G12, G24 |
| Decide by default and record it | no human is available and the choice is reversible | CHRYSOS decide-and-record-never-block; Substrate take-the-sensible-default |
| Ask first | live client system, money, legal wording, irreversible actions | Substrate hard lines |
| Spec before code, including a persistence clause | a product with saved state | CHRYSOS AGENTS.md "Spec-first" |
| Local CI is the gate, cloud CI on request only | the project pays for CI minutes | Substrate ci-runs-locally; CHRYSOS and MIDAS workflow_dispatch |

## Parallel work and worktrees

- **Worktrees work for read-and-audit isolation.** Substrate gives auditors their own database, port and SQLite file.
- **Parallel builders lost on cost in CHRYSOS:** 6 agents used about 2.9M tokens and the session limit killed work twice. Every package touched the same registration files, so N agents meant N-way conflicts. Since 2026-09-25 the rule is to work sequentially and to delegate only a large, isolated package (four-agents-is-the-cap).
- **Traps that cross the worktree boundary:**
  - a shared build directory;
  - a machine-wide `taskkill`;
  - worktrees created from a stale base;
  - Serena edits landing in the main checkout.

## Reusable assets

| Asset | Source | How generic |
|---|---|---|
| register-loop, lusser, adversarial-assurance, epic-orchestrator, npm-slopsquat-guard, audio-plugin-audit skills | ~/.claude/skills, synced copies | generic except audio-plugin-audit |
| Hooks: block_piped_register, block_coupled_push, block_undeclared_npx, no-heredoc-file-write | CHRYSOS .claude/hooks, ~/.claude/hooks | generic after small edits (3 already generalised and tested) |
| Hook positive-control runner | CHRYSOS tools/check_hooks.py | idea generic, code CHRYSOS-specific |
| ADR template with "Revisit if" | client project C docs/adr/ADR-000-template.md | fully generic |
| Definition of Ready and Done, change request, R0 to R4 | client project C docs/standards/ | generic once client names are removed |
| "What every gate owes" | CHRYSOS VERIFICATION.md:124 | generic text |
| Sabotage registry pattern | CHRYSOS src/dsp/core/sabotage.* | pattern portable, code C++ only |
| Docs-currency gate | Substrate scripts/check-docs-current.mjs, docs-map.json | map is per project, mechanism generic |
| Pre-push path matrix, fail closed | Substrate .githooks/pre-push | concept generic, paths not |
| Worktree agent brief | CHRYSOS memory the-worktree-agent-brief | generic |
| Bug-class catalogue | MIDAS docs/BUG_CLASSES.md, CHRYSOS LESSONS_FROM_MIDAS.md | format generic, content audio |
| Engineering guardrails | ~/.claude/engineering-guardrails.md | generic |

## Inconsistencies and duplication

1. **Rule text is copied, then drifts.**
   - The loop is written out in 3 places in CHRYSOS, and 1 copy names a hook removed on 2026-09-30.
   - The rtk and Serena rule appears 3 times.
   - "Measure first" is duplicated between MIDAS and CHRYSOS.
2. **Agent-facing files have grown past use.** CHRYSOS CLAUDE.md is 56 KB, much of it struck-through text. The registers are 600 to 800 KB and have been corrupted by scripted edits.
3. **Ask versus decide.** CHRYSOS nearly bans asking. Client work on a live site requires approval for every live change. lusser requires asking about spec ambiguities. Each is right in its own context, but no project states the rule for choosing.
4. **CI wording.** "Merge only on green CI" sits beside workflow_dispatch-only CI. The real gate is local.
5. **Counts drift.** CHRYSOS: "five PreToolUse guards" against 8 hooks. Substrate CLAUDE.md: 8 CI stages against 13.
6. **Formats drift.** ADR format drifts between projects and inside CHRYSOS. MIDAS has none of the later structure: no hooks, ADRs, register, S0 or lusser.
