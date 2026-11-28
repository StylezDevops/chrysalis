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

## Proportion

Every universal rule is graded as a control, a scaled rule or a practice, and every change has a
class from C0 (small) to C2 (risky). `PROPORTION.md` holds the grades, the classes, what each class
asks for, what enforces each rule, and how a project adapts a rule. Read it before the rules.

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
- A test that cannot run reports itself skipped, never passed. A gate fails when a category of tests
  it requires ran none.
- An assertion that passes whichever way the code behaves is not a test. A validator that only warns
  is a gate that cannot fail.
- Check the gate configuration as well: no step that only echoes, continues on error, or reads a
  report that nothing writes.
- For a whole suite the control is mutation testing with a break threshold. Each surviving mutant is
  a missing test or a recorded equivalent.

Evidence: CHRYSOS VERIFICATION.md "What every gate owes" and S0 sabotage; Substrate storage-layout gate self-test; the in-work project's integration tests that returned early and passed, its echo-only security stages and its mutation config with no threshold.

### U3. A defect becomes structure

A found defect is not fixed and forgotten. At minimum it becomes:

1. a register row with the measured number before and after;
2. a regression test that fails without the fix and passes with it.

Then decide, and record the decision in the row:

3. a new gate, if the defect is a new class that existing gates cannot see;
4. a rule (in the project's CLAUDE.md or here), if the mistake was in how the work was done;
5. an ADR, if fixing it changed a design decision;
6. a bug-class entry (`templates/bug-class.md`), if it is a pattern likely to recur in other code;
7. an entry in the project's list of names that do not exist, if the agent invented an API, field or
   option. The list is read at the start of every session.

Every defect also gets two searches. Hunt its shape across the codebase, a cheap search pass first
and then a careful read of the hotspots, and record what was cleared as well as what was fixed. Find
each existing test that asserted the defective behaviour as correct, and rewrite it.

A finding becomes a register row only if it is reproduced and could change an output a user sees
or a gate's verdict. Anything less is a one-line note.

Evidence: CHRYSOS docs/AUDIT_REGISTER.md and AGENTS.md PR checklist; Substrate register row R-103; MIDAS docs/BUG_CLASSES.md; the in-work project's pattern-catalogue audit, its rewritten tests that had pinned the bug, and its lessons file of model properties that do not exist.

### U4. Tests argue, they do not record

- Sweep the variable; do not pin it. List what each gate pins: that list is the next bug backlog.
- Prefer property assertions ("a notch filter notches") to expected values.
- Never derive the expected value from the code under test. Copy literals from the canonical source.
- When a sweep is meant to vary something, assert that it did vary.
- Test the whole pipeline, not each half.
- Write the test red first and check it fails for the right reason.
- Green tests written by the same agent that wrote the code are the weakest evidence there is. Say
  so when reporting them.
- A unit's tests cover construction, the normal case, edge values, a failing dependency,
  cancellation, both sides of every branch and every field of the output.
- Never mock the code under test. Prove an effect by reading it back from the real target, not from
  the client's reply.
- Give a pager one item more than a page. Push a real create, update and delete through an
  incremental path. Sweep values whose text order differs from their numeric order.
- Draw the test plan from an inventory of every entry point. Coverage exclusions are listed with
  reasons, like suppressions; the code that orchestrates the system and every deployable unit are
  never excluded.
- Integration tests run in a namespace of their own in a real store, created and dropped per run.
  Tests that share global state run alone.
- A claim that new code replaces old needs both run on the same input and the outputs compared.

Evidence: MIDAS memory midas-gate-coverage-doctrine; Substrate memory test-quality-lesson; CHRYSOS memory a-gate-green-where-the-defect-cannot-appear; the in-work project's test categories, per-run test schema, the pager that never left page 1 and its uncovered orchestrator.

### U5. Adversarial audit until a round is clean

After a fix, a fresh-context auditor reviews the change, including the fix itself. Findings are fixed
red-first and the audit runs again. A round that finds only low-severity issues is not clean. Audit
depth is sized to risk: 2 rounds for core, stateful or real-time code; 1 for UI and docs.

Besides its own brief, the auditor works a fixed list: the same job run twice at once, input out of
order, clock and timezone edges, a reused key, throttling, a batch that half fails, orphaned state,
malformed config, and whether each finding holds for its siblings (U21). Each audit is compared with the claims of the one before it. Rejected findings are
logged with the reason.

Evidence: register-loop skill; Substrate memory never-accept-faults; CHRYSOS .claude/register-loop.md; the in-work project's audit graded "A, critical 0" and contradicted by stubs and injection found 15 days later.

### U6. Every fault is owned and on the record

A fault seen is a fault owned, pre-existing or not. What is forbidden is a fault nobody can see: a
deferral marker with no register row, "deliberately not done", a known-failing baseline that is not a
list of defects. Each fault has a register row in one of four states:

| State | Meaning | The row needs |
|---|---|---|
| OPEN | Not yet fixed. Blocks a release: `register check --release` fails. | the defect and its measure |
| CLOSED | Fixed (U3). | before and after numbers, a regression test, a follow-up decision |
| SCHEDULED | To be fixed later, because it cannot reach a user, data or a gate verdict before then. | `scheduled: OWNER, due YYYY-MM-DD, reason` |
| ACCEPTED | A known risk left in place on purpose. | `accepted: NAME (human, YYYY-MM-DD), revisit YYYY-MM-DD, reason` |

- Only a human with authority over the project accepts a risk. An agent may propose SCHEDULED or
  ACCEPTED; it never records the decision itself.
- A due or revisit date that has passed fails `register check`.
- A marker in code cites its row, as in `TODO(R-12)`. The deferral hook refuses a marker with no
  citation, and `doctor` fails a citation whose row is missing or CLOSED. A marker closes with a test
  of the behaviour, never with a reworded comment.
- Lowering a severity to get past a check is gaming the check.

Evidence: Substrate memories fix-never-defer and never-accept-faults; CHRYSOS memory a-problem-seen-is-owned; the in-work project's 30 "for now" items, some closed by rewording the comment, and its lint fixed by downgrading errors to warnings. The SCHEDULED and ACCEPTED states came from the outside review of 2026-11-28: the absolute form left no honest way to record a risk a team had decided to carry.

### U7. A repeatable mistake gets a hook

When an agent makes a mistake of a shape a machine can recognise, write a hook that refuses it,
rather than a resolution to remember. Every hook states the incident behind it, what it does not
catch, and ships with a test of block cases and allow cases (see `hooks/`). A checklist ticked by hand
is a candidate too: each item becomes a hook or a test, and a security checklist's claims are asserted
against the code they describe.

Evidence: the in-work project's 40-item pre-commit checklist with no hooks, and its security checklist ticked against templates that said the opposite; CHRYSOS .claude/hooks/ (8 hooks, each with WHY and NOT-CATCH sections) and gate H10; CHRYSOS memory trust-the-number-not-the-prose.

### U8. One source of truth

Each fact, rule or mapping is written once and referenced. Where 2 copies cannot be avoided,
something diffs them mechanically and fails on drift.

- Two types or validators doing one job are a defect. The primary, fallback and retry paths call one
  implementation.
- Contracts that cross a language boundary, such as a stored procedure and its caller, are compared
  by a check.
- Where two documents must both exist, one of them says it wins.

Evidence: CHRYSOS tools/check_gate_parity.py; Substrate docs/docs-map.json and API reference completeness test; the in-work project's five divergent identifier validators and its retry path with its own copy of the mapping.

### U9. Docs move with code

A change to behaviour updates its docs in the same branch. A reversed decision is struck through and
dated, not deleted. Keep files an agent reads every session short; move history to an archive file.
INFERRED limit: an agent-facing file over about 25 KB is a defect, and so is a source file over about
500 lines.

Docs are claims that can be run. Config examples are parsed by the real loader in a test, each
command is run once, worked numbers come from the code, links resolve, and every capability names its
implementation or is marked planned.

Evidence: Substrate scripts/check-docs-current.mjs; CHRYSOS CLAUDE.md struck-through reversals; the in-work project's guide examples run as tests, against reference examples its own loader rejects and a rollback API documented with three endpoints that do not exist. The 25 KB limit is INFERRED from CHRYSOS CLAUDE.md (56 KB) having outgrown use; the 500-line limit is the in-work project's.

### U10. lusser, scaled to the change

Work of class C1 or C2 has a `.lusser/` spec: numbered clauses, ambiguities resolved by a human before
building, a part budget, and checks that fail differently from an agent. C1 work may use
`templates/lusser/spec-minimal.md` (1 clause, 1 check, budget 1 or 2); C2 work has a full spec. A C0
change needs no spec: its commit message states what it claims and the check that shows it. `lusser
check` must pass before C1 or C2 work is called done.

Evidence: .lusser/ in CHRYSOS and Substrate. Made mandatory for all work on 2026-11-25; scaled by class on 2026-11-28 after an outside review found it heavier than small work needs.

### U11. Decisions carry their reasons

Lasting decisions get an ADR (`templates/adr.md`): context, options considered including the rejected
ones, decision, consequences, and a "Revisit if" condition. Number ADRs in sequence and never
renumber. Reserve the number before an agent starts work that will need one.

- An ADR that holds several decisions keeps a numbered register of them, each with a status.
- Plans and ADRs price the cheaper alternative and cite the seams by file and line.
- Code cites the decision ID where it applies the decision.
- A config default carries its reason beside it.

Evidence: CHRYSOS decisions/ (184 ADRs) and AGENTS.md "Decisions"; CHRYSOS memory parallel-agents-collide-on-ids; the in-work project's platform ADR with its decision register D1 to D17 and its code comments citing them.

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
- A number that was not measured says so. A progress note names what was not verified.
- A count of the places that comply proves nothing without a search for the places that do not.

Evidence: CHRYSOS memories the-worktree-agent-brief and trust-the-number-not-the-prose; CHRYSOS hooks block_piped_register and block_coupled_push; the in-work project's "656 sites, all compliant" audit and its progress notes that say what was asserted and what was not.

### U14. Ask or decide

Default: take the recommended route, record it with its date and the assumption behind it, and keep
working. Park open questions in the handover, not in a blocking prompt.

Always ask first for:

- lusser spec ambiguities (U10);
- any R3 or R4 action on a live system (K1);
- anything involving money, legal or claims wording, or personal data policy;
- irreversible or outward-facing actions: deleting, force-pushing, publishing, sending, deploying;
- public surface the spec does not name: a route, endpoint, command or config option.

Evidence: CHRYSOS memory decide-and-record-never-block; Substrate memory take-the-sensible-default; the in-work project's lesson that an ADR line was no licence for a parallel route set; decided 2026-11-25.

### U15. Test what changed

Each change closes on: the build, the unit tests, the gates whose files or subjects were touched, and
the fast static gates. Run the full gate set only for a cross-cutting change (shared state, real-time
path, build system, the gate tooling itself), before a release, or when asked.

A refactor changes structure only. It starts from passing tests, goes in small commits, and never
changes behaviour in the same commit.

Evidence: CHRYSOS memory registers-once-per-batch (2026-10-05, 2026-10-10); Substrate scripts/ci-local.sh --changed; the in-work project's refactoring plan rules.

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

### U17. Fail closed

When a prerequisite, setting, environment signal, guard dependency or evidence store is missing, the
work stops with an error that says what failed, on which item, and what to do next.

- No default that changes behaviour: an unset environment is not "development".
- No placeholder value standing in for required data.
- A guard whose dependency is absent does not skip itself and let the action run.
- A step that checks or restores safety never continues on failure.
- Continuing past a failure is allowed only when config declares it, and the result counts it.

Evidence: the in-work project's unset environment defaulting to development and opening anonymous endpoints; its validator that "assumes things are fine"; its self-healing truncate that ran after its safety check was skipped; its deploy that invented resource names.

### U18. Every unit has one outcome

Each unit of work (a record, request, file or test) ends in exactly one recorded outcome.

- Counts reconcile exactly, with no tolerance. Counters count outcomes, not attempts.
- A result never says success beside a failure.
- A progress marker (watermark, checkpoint, cursor) is taken before the read and moves only past
  outcomes that are durably recorded. With no store for failures, the run stops and the marker stays.
- Parallel work records the set of finished items, not the highest index finished.

Evidence: the in-work project's delta sync, which quarantines every failure and fails rather than move the watermark when it cannot; and against that, its watermark taken after the read, its 5% count tolerance and its "Completed" reported with failures.

### U19. Config is checked when it loads

Configuration is validated against a schema when it loads, and again before each run.

- An unknown key, an option that is accepted but ignored, and a forbidden combination of options are
  errors, not silent no-ops.
- Each option has a test showing that it changes behaviour. Config that nothing reads is a defect.
- Every output, cache entry and error record carries a fingerprint of the effective config and code
  version. A resumed run refuses to continue when the fingerprint has changed.

Evidence: the in-work project's config checksum on every run and rejection; and against that, its options documented but never read and its 155 ad hoc environment reads with no startup validation.

### U20. A mechanism counts once it is shown to run

A middleware, hook, registered service, alert, gate step or option counts only when there is
evidence that it ran on a real path.

- A stub or scaffold throws. It never returns success, an empty list or zero.
- A feature is done when its claim names its implementation and a run shows it working.

Evidence: the in-work project's security-headers middleware, inert for about 10 months until its first run exposed a header that threw on every response; its simulated-success delta stub; its validators returning empty lists.

### U21. One promise, every member

When the software promises a behaviour across a family of interchangeable things, the promise holds
for every member. Where it does not, the docs say which members it covers and why the others cannot
fail that way.

A family is any set of things a caller can swap without changing its own code: storage backends,
payment providers, databases, deployment targets, the actors who can do the same job (a person, a
role, an agent) and the routes or tools that write the same fact.

- A defect found in one member is checked against every sibling in the same change. It is fixed for
  each member it can reach, and the commit says why it cannot reach the rest.
- The test for the behaviour runs once per member, so a member added later fails until it keeps the
  promise.
- Every audit brief asks whether each finding holds for the siblings (U5). A finding fixed for one
  member only is not closed.
- Docs state the promise once, for the whole family, and name any member that differs. They never
  state it for one member and leave the reader to assume it for the rest.

Evidence: the owner's decision of 2026-11-27, in Substrate's local CLAUDE.md ("One promise, every implementation"), after Substrate R-321 kept a promise for one storage backend only; chrysalis R-11, where R-8 reached `worktree` but not `lusser parts`.

---

## Conditional rules

| ID | Applies when (config) | Rule | Evidence |
|---|---|---|---|
| K1 | `risk.live_production` | Classify every action R0 to R4 before taking it (below). R3 and R4 need a human's approval for that one action and a written rollback. Silence is not approval. If unsure of the class, take the higher one. | client project C change-control standard |
| K2 | `stage == "pre-release"` and not `risk.live_production` | No compatibility code: no backfills, shims, interim states or dual paths. The rule expires at the first real release and then inverts into K3. | Substrate principle-pre-release-no-legacy.md |
| K3 | `risk.live_production` | Migrations are idempotent, reversible, and tested on a copy of production data before they ship. A deploy checklist holds only what cannot be automated; the rest is checked when the service starts and reported by a health check that probes its real dependencies. Each deploy is verified against the deployed target and rolled back by script when verification fails. | client project B CLAUDE.md "Backwards compatibility"; the in-work project's deployment checklist and startup checks |
| K4 | `risk.handles_money` or `risk.handles_personal_data` or `risk.auth` | Each feature answers a written threat model (`templates/threat-model.md`) in its PR, and attack scenarios run as automated tests that must fail to break in. | Substrate CLAUDE.md section 14 |
| K5 | `risk.realtime` | Real-time paths do no allocation, locking, file or network I/O. A gate proves it under a guard, and the gate has a positive control. | CHRYSOS VERIFICATION.md G6; MIDAS CLAUDE.md |
| K6 | `"web"` in `stack.platforms` | A performance budget is a gate. Blowing it blocks the release. | client project B CLAUDE.md performance budget |
| K7 | `ci.remote == "on-request"` | The local gate runner is the gate. Remote CI runs only when asked, or before a release. Docs must not claim "merge on green CI" while this holds. | Substrate memory ci-runs-locally; CHRYSOS and MIDAS ci.yml workflow_dispatch |
| K8 | `risk.client_engagement` | A human approves every change to the client's live system. Client names, data and credentials never leave the client's repository. | client project C CLAUDE.md; decided 2026-11-25 |
| K9 | `risk.live_production` | Before anything above R1, a verified backup exists and a restore has actually been performed. | client project C ready-and-done standard (verified restore first) |
| K10 | `risk.mutates_data` | Before writing code that moves data, trace its journey: source format, each transform, one transform shared by the bulk, single and retry paths, destination types, required fields, and defaults the write method skips. Deletes inferred from absence need a read proven complete, a cap on the share deleted, and margins that err toward keeping. Undo data is captured before each write, on every path. A switch-off and switch-on pair restores each item's recorded prior state, in a step that always runs. A transform never changes a record's key. A destructive operation needs a confirmation and more privilege than a read. A dry run has no side effects. A run stops itself when its failure rate shows a systemic fault. | the in-work project's delete guard rails, circuit breaker and data-journey questions; against that, its rollback plans built only after success and its re-enable that turned on items that were off |
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
