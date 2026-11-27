# The method

Each rule has an ID. Project files cite the ID; they do not copy the text. Evidence for every rule is
in `docs/discovery.md`. A rule marked INFERRED was read off practice, not found written down.

Universal rules (U) apply to every project. Conditional rules (K) apply when their condition holds;
`chrysalis.py rules` selects them from `config_project.json`. Project-specific rules live in the
project, not here.

General code-writing guardrails (reuse before building, verify before trusting, security baseline,
editing discipline) live in `~/.claude/engineering-guardrails.md`. `chrysalis.py apply` installs a
copy there if it is absent. This file does not repeat them.

---

## Universal rules

### U1. Measure first

Reproduce the defect as a number through the path that ships. Prove the detector sees it. Localise
it (where, when, which setting). Then form one hypothesis, change one thing, and measure again.

- Do not name a cause in prose, a comment or a commit until it is measured.
- A change that makes no difference is a result: the thing changed was not the cause. Go back to
  reproducing; do not reach for the next guess.
- Reading a code path is not evidence that it runs, or that a user can reach it.

Evidence: MIDAS CLAUDE.md "MEASURE FIRST"; CHRYSOS CLAUDE.md; Substrate .claude/register-loop.md.

### U2. A check must be able to fail

Before a green result counts, show the check going red on the defect it exists for: a positive
control, a sabotage injection, or reverting the fix and watching the number move back.

- The control names the clause it proves, by ID. A check that went red near the defect but for a
  different reason proves nothing.
- A gate that has never failed is not a gate.
- When a control does not move the reading, the detector is pointed at something else. Look
  downstream for a stage doing the work.

Evidence: CHRYSOS VERIFICATION.md "What every gate owes" and S0 sabotage; Substrate storage-layout gate self-test.

### U3. A defect becomes structure

A found defect is not fixed and forgotten. At minimum it becomes:

1. a register row with the measured number before and after;
2. a regression test that fails without the fix and passes with it.

Then decide, and record the decision in the row:

3. a new gate, if the defect is a new class that existing gates cannot see;
4. a rule (in the project's CLAUDE.md or here), if the mistake was in how the work was done;
5. an ADR, if fixing it changed a design decision;
6. a bug-class entry, if it is a pattern likely to recur in other code.

A finding becomes a register row only if it is reproduced and could change an output a user sees
or a gate's verdict. Anything less is a one-line note.

Evidence: CHRYSOS docs/AUDIT_REGISTER.md and AGENTS.md PR checklist; Substrate register row R-103; MIDAS docs/BUG_CLASSES.md.

### U4. Tests argue, they do not record

- Sweep the variable; do not pin it. List what each gate pins: that list is the next bug backlog.
- Prefer property assertions ("a notch filter notches") to expected values.
- Never derive the expected value from the code under test. Copy literals from the canonical source.
- When a sweep is meant to vary something, assert that it did vary.
- Test the whole pipeline, not each half.
- Write the test red first and check it fails for the right reason.
- Green tests written by the same agent that wrote the code are the weakest evidence there is. Say
  so when reporting them.

Evidence: MIDAS memory midas-gate-coverage-doctrine; Substrate memory test-quality-lesson; CHRYSOS memory a-gate-green-where-the-defect-cannot-appear.

### U5. Adversarial audit until a round is clean

After a fix, a fresh-context auditor reviews the change, including the fix itself. Findings are fixed
red-first and the audit runs again. A round that finds only low-severity issues is not clean. Audit
depth is sized to risk: 2 rounds for core, stateful or real-time code; 1 for UI and docs.

Evidence: register-loop skill; Substrate memory never-accept-faults; CHRYSOS .claude/register-loop.md.

### U6. Fix, never defer

A fault seen is a fault owned, pre-existing or not. Faults are not marked "accepted". Only the project
owner can decide to leave one, and only by saying so.

Evidence: Substrate memories fix-never-defer and never-accept-faults; CHRYSOS memory a-problem-seen-is-owned.

### U7. A repeatable mistake gets a hook

When an agent makes a mistake of a shape a machine can recognise, write a hook that refuses it,
rather than a resolution to remember. Every hook states the incident behind it, what it does not
catch, and ships with a test of block cases and allow cases (see `hooks/`).

Evidence: CHRYSOS .claude/hooks/ (8 hooks, each with WHY and NOT-CATCH sections) and gate H10; CHRYSOS memory trust-the-number-not-the-prose.

### U8. One source of truth

Each fact, rule or mapping is written once and referenced. Where 2 copies cannot be avoided,
something diffs them mechanically and fails on drift.

Evidence: CHRYSOS tools/check_gate_parity.py; Substrate docs/docs-map.json and API reference completeness test.

### U9. Docs move with code

A change to behaviour updates its docs in the same branch. A reversed decision is struck through and
dated, not deleted. Keep files an agent reads every session short; move history to an archive file.
INFERRED limit: an agent-facing file over about 25 KB is a defect.

Evidence: Substrate scripts/check-docs-current.mjs; CHRYSOS CLAUDE.md struck-through reversals. The 25 KB limit is INFERRED from CHRYSOS CLAUDE.md (56 KB) having outgrown use.

### U10. lusser on all work

Every piece of work, whatever its size, has a `.lusser/` spec: numbered clauses, ambiguities resolved
by a human before building, a part budget, and checks that fail differently from an agent. Small work
uses `templates/lusser/spec-minimal.md` (1 clause, 1 check, budget 1 or 2). `lusser check` must pass
before work is called done.

Evidence: .lusser/ in CHRYSOS and Substrate. Mandatory regardless of size: decided 2026-11-25.

### U11. Decisions carry their reasons

Lasting decisions get an ADR (`templates/adr.md`): context, options considered including the rejected
ones, decision, consequences, and a "Revisit if" condition. Number ADRs in sequence and never
renumber. Reserve the number before an agent starts work that will need one.

Evidence: CHRYSOS decisions/ (184 ADRs) and AGENTS.md "Decisions"; CHRYSOS memory parallel-agents-collide-on-ids.

### U12. Sessions hand over

Write the handover before context runs out (threshold 85%). The handover carries the loop itself,
verbatim, plus where work stopped and what is open. Every session starts by reading it and closes by
rewriting it, including sessions that changed nothing.

Evidence: register-loop skill (85% threshold); CHRYSOS docs/HANDOVER-*.md.

### U13. A report is a claim

- Read the diff, not the summary. Re-run headline numbers yourself before repeating them.
- Read the exit code, not the prose. Never pipe a gate's output; redirect it to a file, read the code,
  then read the file.
- A verification and an irreversible action never share a command.
- A tool reporting success is a claim. Check the effect.

Evidence: CHRYSOS memories the-worktree-agent-brief and trust-the-number-not-the-prose; CHRYSOS hooks block_piped_register and block_coupled_push.

### U14. Ask or decide

Default: take the recommended route, record it with its date and the assumption behind it, and keep
working. Park open questions in the handover, not in a blocking prompt.

Always ask first for:

- lusser spec ambiguities (U10);
- any R3 or R4 action on a live system (K1);
- anything involving money, legal or claims wording, or personal data policy;
- irreversible or outward-facing actions: deleting, force-pushing, publishing, sending, deploying.

Evidence: CHRYSOS memory decide-and-record-never-block; Substrate memory take-the-sensible-default; decided 2026-11-25.

### U15. Test what changed

Each change closes on: the build, the unit tests, the gates whose files or subjects were touched, and
the fast static gates. Run the full gate set only for a cross-cutting change (shared state, real-time
path, build system, the gate tooling itself), before a release, or when asked.

Evidence: CHRYSOS memory registers-once-per-batch (2026-10-05, 2026-10-10); Substrate scripts/ci-local.sh --changed.

### U16. Parallel work is earned

Default: one builder at a time. The cap on concurrent agents is `agents.max_parallel_agents` (1 to 8).
Delegation pays only when the package is large enough to cover the agent re-reading the project rules,
and isolated enough not to need reconciling. Read-only audits are the best use.

Worktree procedure:

1. Create the worktree from the current `main`, then have the agent fast-forward and report its base.
2. Give it its own build directory, ports, database and temp folders.
3. It must not run the full gate set, push, or edit shared registration files. It returns the exact
   text for each shared file and the main session applies it.
4. If an editor tool is bound to the main checkout (for example Serena), the agent uses it for reading
   only.
5. After merging, the main session runs `git status --porcelain` and `git diff --exit-code` on its own
   checkout, then removes the worktree, its branch and its build directory with
   `chrysalis.py worktree finish NAME --build-dir DIR`.
6. At the end of a session, `chrysalis.py worktree sweep` lists every merged agent branch
   (`agent/*`, `worktree-agent-*`) and its worktree; `--apply` removes them. Unmerged or dirty ones stay.

Do not use worktrees when every package touches the same files, when the build tree or machine-wide
processes cannot be isolated, or when the work fits in the main session.

Evidence: CHRYSOS memories four-agents-is-the-cap, subagent-worktrees-preferred, the-worktree-agent-brief; Substrate worktree-agent-* branches left after merge; decided 2026-11-25.

---

## Conditional rules

| ID | Applies when (config) | Rule | Evidence |
|---|---|---|---|
| K1 | `risk.live_production` | Classify every action R0 to R4 before taking it (below). R3 and R4 need a human's approval for that one action and a written rollback. Silence is not approval. If unsure of the class, take the higher one. | client project C change-control standard |
| K2 | `stage == "pre-release"` and not `risk.live_production` | No compatibility code: no backfills, shims, interim states or dual paths. The rule expires at the first real release and then inverts into K3. | Substrate principle-pre-release-no-legacy.md |
| K3 | `risk.live_production` | Migrations are idempotent, reversible, and tested on a copy of production data before they ship. | client project B CLAUDE.md "Backwards compatibility" |
| K4 | `risk.handles_money` or `risk.handles_personal_data` or `risk.auth` | Each feature answers a written threat model (`templates/threat-model.md`) in its PR, and attack scenarios run as automated tests that must fail to break in. | Substrate CLAUDE.md section 14 |
| K5 | `risk.realtime` | Real-time paths do no allocation, locking, file or network I/O. A gate proves it under a guard, and the gate has a positive control. | CHRYSOS VERIFICATION.md G6; MIDAS CLAUDE.md |
| K6 | `"web"` in `stack.platforms` | A performance budget is a gate. Blowing it blocks the release. | client project B CLAUDE.md performance budget |
| K7 | `ci.remote == "on-request"` | The local gate runner is the gate. Remote CI runs only when asked, or before a release. Docs must not claim "merge on green CI" while this holds. | Substrate memory ci-runs-locally; CHRYSOS and MIDAS ci.yml workflow_dispatch |
| K8 | `risk.client_engagement` | A human approves every change to the client's live system. Client names, data and credentials never leave the client's repository. | client project C CLAUDE.md; decided 2026-11-25 |
| K9 | `risk.live_production` | Before anything above R1, a verified backup exists and a restore has actually been performed. | client project C ready-and-done standard (verified restore first) |
### Blast-radius classes (K1)

| Class | Meaning | Gate |
|---|---|---|
| R0 | local only | none |
| R1 | read-only against live | log it |
| R2 | staging or a copy only | log it |
| R3 | reversible change on live | human approval and a written rollback |
| R4 | hard to reverse | approval, verified backup, agreed window, rehearsed rollback |

A rollback you have only imagined is R4.

---

## The register loop

The working loop for defects is the `register-loop` skill (`skills/register-loop/`). It applies U1 to
U5 one row at a time. Its per-project settings go in `.claude/register-loop.md`.
