# Discovery report

Date: 2026-11-25; the in-work project section added 2026-11-27. Read-only investigation. Nothing in
any source project was changed.

## Scope

| Project | Kind | History | Evidence read |
|---|---|---|---|
| In-work project | data-integration platform at work, where the method began; not named here | from late 2025 | every doc and internal note in full, agent rules and memories, code mapped and sampled (see its section below) |
| Client web projects | evidence read under their own change-control rules, not listed here | | |
| Substrate | owned web3 product (FastAPI, SvelteKit, Solidity) | 1047 commits, 2026-06-13 to now | CLAUDE.md, .lusser, register, pre-push, 81 memories |
| MIDAS | owned audio plugin (C++/JUCE) | 2026-07-02 to 2026-09-11 | CLAUDE.md, VERIFICATION.md, BUG_CLASSES.md, 81 memories |
| CHRYSOS | owned audio plugin (C++/JUCE) | 1030 commits, 2026-09-10 to now | CLAUDE.md, AGENTS.md, VERIFICATION.md, 184 ADRs, hooks, 98 memories |
| Global | ~/.claude | n/a | CLAUDE.md, engineering-guardrails.md, skills, hooks |

Two subagents read the source projects. 9 of their claims were checked against the files and all held.

## The method, as it evolved

INFERRED from dates. The same method gets stricter with each project.

0. **The in-work project (from late 2025):** where the method began. Prerequisite validation, zero warnings, a ban on "for now" code, one transformation for every path, records written or quarantined and never dropped, and ADRs with a register of numbered decisions. Its rules were prose in agent instruction files, with no hooks, which is why several of them were broken in practice (see its section below).
1. **Client web work (from April):** written rules arrive: a test pyramid, a threat model for each feature, attack scenarios that must fail, performance budgets, conventional commits.
2. **MIDAS (July):** "measure before reasoning" becomes a hard rule. Numbered gates. A bug-class catalogue (`docs/BUG_CLASSES.md`, C1 to about C81).
3. **CHRYSOS (September):** adds PreToolUse hooks born from incidents, ADRs, the defect register, the S0 sabotage gate that proves every gate can fail, gate parity checks and lusser.
4. **Substrate (same period):** carry the loop across as the `register-loop` skill. They add a docs-currency gate, a fail-closed pre-push path matrix, and blast-radius classes for live systems.

## Universal rules (found in several projects)

The numbers in this table are the working numbers from the first discovery pass. `METHOD.md`
renumbered them and added U14 to U20 later, so cite rules by their `METHOD.md` ID, not by these.
The table records what discovery found, not the rules in force: for those, read `METHOD.md` and
`PROPORTION.md`, which grades every rule and scales it by change class.

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
| U9 | ~~**Fix, never defer.**~~ A problem seen is owned, pre-existing or not. ~~Only the project owner can leave a fault in place.~~ Superseded 2026-11-28 by METHOD U6: every fault is on the record as OPEN, CLOSED, SCHEDULED or ACCEPTED. | Substrate fix-never-defer, never-accept-faults; CHRYSOS a-problem-seen-is-owned; global guardrails section 4 |
| U10 | **lusser.** Numbered clauses, ambiguities resolved by a human, a part budget, and check kinds that fail differently from an agent. | .lusser/ in CHRYSOS and Substrate |
| U11 | **Decisions carry their reasons.** Rejected alternatives, measurements and a revisit condition. | CHRYSOS decisions/; Substrate dated inline decisions |
| U12 | **Sessions hand over.** Write the handover at about 85% context. Start and close rituals. | register-loop skill; CHRYSOS HANDOVER-*.md |
| U13 | **A report is a claim.** Read the diff, not the summary. Read the exit code, not the prose. Keep verification and an irreversible action out of the same command. | CHRYSOS the-worktree-agent-brief, block_piped_register, block_coupled_push |

U21 (one promise, every member) is not a discovered practice. The owner decided it on 2026-11-27 after
Substrate R-321, where a guarantee was built for one storage backend while its siblings went without,
and recorded it in Substrate's local CLAUDE.md, which is gitignored there. Chrysalis hit the same shape the same day: R-8 fixed the base branch for `worktree` and
missed `lusser parts` (R-11).

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

## The in-work project (read 2026-11-27)

The in-work project is where the method began. It is a data-integration platform: about 119,000 lines
of production C#, 80,000 lines of tests (3,283 of them), and 2.4 MB of docs and internal notes. It
was built mostly in an editor with AI extensions, so its rules live in agent instruction files, tool
memories and long internal documents rather than in hooks. Every doc and internal note was read to
its last line. The code was mapped and sampled rather than read whole.

It contributes in two ways. Some practices it does well and the later projects never carried
forward. Others are defects that show a rule was missing. Each rule added from it names its evidence
in METHOD.md.

**Practices it does well, now in the method:**

| Practice | Where it went |
|---|---|
| Every record ends written or quarantined; the watermark does not move past an unrecorded failure; outcomes are counted, not attempts | U18 |
| A checksum of the effective config on every run and every rejected record | U19 |
| Deletes inferred from absence guarded by a complete read, a ratio cap and margins that err toward keeping | K10 |
| A run that stops itself when its rejection rate shows a systemic fault | K10 |
| The "trace the data journey" questions before writing data code | K10 |
| Guide examples run as tests against the real loader | U9 |
| A found bug turned into a pattern catalogue that drives a codebase-wide hunt, recording what was cleared | U3, audit-record template |
| Tests that asserted the bug as correct were rewritten | U3 |
| A lessons file of model properties that do not exist | U3, names-that-do-not-exist template |
| An ADR holding a register of 17 numbered decisions, each with a status, a "what review changed" section and open items by owner | U11, ADR template |
| Fix records that state what the fix does not change and what could not be tested | fix-record template |
| A deploy checklist holding only what cannot be automated, the rest checked at startup | K3, runbook template |
| A per-run schema in a real database for integration tests; tests sharing environment variables run alone | U4 |
| Refactors that start from passing tests and change no behaviour | U15 |
| Code comments that cite the decision ID they apply | U11 |

**Defects that show a missing rule:**

| Defect | Rule it led to |
|---|---|
| An unset environment defaulted to development and opened anonymous endpoints; a validator "assumes things are fine" when it cannot read its setting; a truncate ran after its safety check was skipped | U17 |
| A watermark taken after the read lost rows; count checks with a 5% tolerance; "Completed" reported beside failures | U18 |
| Options documented and accepted but never read; no startup validation of 155 environment reads | U19 |
| A security middleware inert for about 10 months; a delta stub that only incremented its success counter; validators returning empty lists | U20 |
| 18 integration tests that returned early and passed; mutation testing with no threshold; security pipeline stages that only echoed | U2 |
| An audit graded "A, critical 0", contradicted by stubs and SQL injection found 15 days later | U5 |
| 30 "for now" items, some closed by rewording the comment; lint fixed by lowering errors to warnings | U6, deferral-marker hook |
| A 40-item checklist ticked by hand with no hooks; a security checklist ticked against templates that said the opposite | U7 |
| Five identifier validators that had drifted apart; a retry path with its own copy of the mapping | U8 |
| Reference examples the loader rejects; rollback documented with endpoints that do not exist | U9 |
| Rollback plans built only after a successful run; a re-enable step that switched on items that were off before | K10 |

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
