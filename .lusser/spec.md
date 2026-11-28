# Spec: Chrysalis, a reusable engineering framework built from my existing method

Context: the method already exists across my projects, including MIDAS, Substrate and
CHRYSOS (see docs/discovery.md). This repo extracts it into 1 canonical, configurable source
that can be cloned into a new project or laid over an existing one without damaging it.

Budget: 36 parts
Assumed p: 0.95

## Clauses

- C1. Every rule in METHOD.md cites at least 1 source file in an existing project, or is labelled INFERRED with the reasoning. No rule exists only because a textbook says so.
- C2. Every rule is classed as universal, conditional (with a predicate over config fields) or project-specific. Conditional rules are selected from config_project.json, not by hand.
- C3. `config_project.json` is validated by a stdlib-only script. Missing or contradictory fields are reported as numbered questions, and the init stops until they are answered.
- C4. [critical] Initialising into an existing repository changes no file that existed before the run. Every proposed change to an existing file is written as a proposal (diff or section in initial.md), never applied.
- C5. [critical] Initialising never deletes, renames, commits, pushes, rewrites history or changes remote settings.
- C6. Initialising an existing repository first produces an inventory of what is already there: CLAUDE.md and AGENTS.md, .claude/ (settings, hooks, skills, rules), .lusser/, ADRs, registers, specs, CI, branches and worktrees. Already-present equivalents are reused, not duplicated.
- C7. Initialising a new project produces initial.md (purpose, users, architecture, constraints, risks, approach), a starter backlog (epics, stories, acceptance criteria), a gate list and a CLAUDE.md that points at the framework rules instead of copying them.
- C8. Every gate the framework defines states its purpose, its run command or human procedure, its pass/fail condition, and whether it is automated or human. Every automated gate ships with a positive control that makes it fail.
- C9. A defect recorded through the framework produces, at minimum, a register row with a measured number and a regression test that fails without the fix. Whether it also produces a gate, rule or ADR is a recorded decision.
- C10. Every hook shipped by the framework has a test with block cases and allow cases, and the tests run in 1 command.
- C11. Each rule text exists once in the framework. Generated project files reference it. Where a copy is unavoidable, a check diffs the 2 copies.
- C12. The worktree procedure covers creation from the current base, isolated build directories, ports and databases, and cleanup after merge: one worktree with its branch and build directory, and a sweep of every merged agent branch and worktree left behind. It also states when not to use worktrees.
- C13. The framework is validated against copies of 2 substantially different existing repositories and 1 new project. For each existing repo, every pre-existing file's hash is identical before and after init.
- C14. Rules, templates and hooks drawn from the in-work project cite it only as "the in-work project". No tracked file names it, its client or its people, and a test proves it.
- C15. Every universal rule is graded once in PROPORTION.md as a control, a scaled rule or a practice, with what it asks of a C0, C1 and C2 change and what enforces it. `classify` reads a diff, works out the lowest class the change may take with its reasons, prints that class's obligations from the table, and refuses a declared class below it. A C0 change carries fewer obligations than a C1, and a C1 fewer than a C2. A project may adapt a practice or a scaled rule only with a human decision, a reason and a revisit date; a control cannot be adapted.
- C16. A register row is OPEN, CLOSED, SCHEDULED or ACCEPTED, and nothing else. SCHEDULED needs an owner, a due date and a reason; ACCEPTED needs a human decision with its date, a revisit date and a reason. A past due or revisit date fails the check, and `--release` fails on any OPEN row. A deferral marker in code is refused unless it cites a register row, and a cited row that is missing or CLOSED fails `doctor`.
- C17. `doctor` checks a project's compliance in 1 read-only command (config and adaptations, register, markers, gates, lusser, agent contract against the rules in force, handover) and exits 1 on any failure. apply proposes a CI workflow that runs it. METHOD.md says, rule by rule, what is enforced by a machine and what relies on people.
- C18. Nothing in the method needs Claude Code. apply writes AGENTS.md as the agent-neutral contract and a CLAUDE.md that imports it; every hook can be called without Claude Code through 1 adapter, and the deferral hook ships for the pre-commit framework. `skills install` never overwrites an existing skill. A pilot guide says how a team measures the method's overhead and adapts it.

## Ambiguities

- A1. Q: Repo name?
      Resolution: chrysalis. (human, 2026-11-25)
- A2. Q: Do the skills and hooks live in this repo, or in a separate repo that this one references?
      Resolution: In this repo, as skills/ and hooks/. (human, 2026-11-25)
- A3. Q: Default for asking versus deciding. Proposed: decide by default and record it, except for lusser spec ambiguities, any R3/R4 action on a live system, money, legal wording, and irreversible or outward-facing actions. Is that the rule for all projects?
      Resolution: Decide and record by default. Ask for lusser spec ambiguities, R3/R4 actions on a live system, money, legal wording, and irreversible or outward-facing actions. (human, 2026-11-25)
- A4. Q: On an existing repo, may init append a clearly marked section to an existing CLAUDE.md, or must every change to an existing file stay a proposal (C4 as written)?
      Resolution: Proposals only. Init never edits an existing file. (human, 2026-11-25)
- A5. Q: Should the framework define agent personas?
      Resolution: No. The working flow is the register loop plus audit agents. (human, 2026-11-25)
- A6. Q: ADRs. Are they universal (CHRYSOS, client project C), or conditional, with dated inline decisions acceptable for smaller projects (Substrate)?
      Resolution: ADRs are universal, using the client project C template with 'Revisit if'. (human, 2026-11-25)
- A7. Q: Test cadence. Is "test what changed; full run only for cross-cutting changes or on request" (CHRYSOS 2026-10-05, Substrate --changed) the default for every project?
      Resolution: Test what changed. Full run only for cross-cutting changes or on request. (human, 2026-11-25)
- A8. Q: CI policy. Is "local CI is the gate, cloud CI only on request" the default, or a per-project cost setting?
      Resolution: Local CI is the gate. Cloud CI on request, set per project. (human, 2026-11-25)
- A9. Q: Parallel agents. Proposed default: builders sequential; worktrees for fresh-context audits and for packages that touch no shared registration files; at most 1 or 2 agents. Agree?
      Resolution: Builders sequential by default. Worktrees for audits and isolated packages. The agent cap is a config value from 1 to 8 (max_parallel_agents); default 2, decided by default under A3. (human, 2026-11-25)
- A10. Q: lusser. Mandatory for every feature, or only above a size threshold (for example more than 1 session of work)?
      Resolution: lusser is mandatory for all work, whatever its size. (human, 2026-11-25)
- A11. Q: Validation targets for C13. Proposed: a copy of CHRYSOS (C++ audio, heavy existing setup) and a copy of a client web project. Substrate instead of either?
      Resolution: Throwaway copies of CHRYSOS and Substrate (heavy existing setup, different stacks) and of MIDAS and the CSAW repo (partial setup); the new-project case is an empty folder holding only the CSAW brief and its Python reference. All are my own projects. No client project is used, named or copied into this repo; repo paths are passed as arguments, never hard-coded. (human, 2026-11-25)
- A12. Q: Naming?
      Resolution: Neutral naming. (human, 2026-11-25)
- A13. Q: Does the framework vendor a copy of ~/.claude/engineering-guardrails.md, or point at the global file and install it if absent?
      Resolution: Point at the global guardrails file; install it if absent. (human, 2026-11-25)
- A14. Q: Part budget. 14 is proposed: METHOD.md, config schema, init script, init skill, templates set, gate template and runner, register template, hooks set, hook test runner, worktree procedure, docs-currency check, lusser tests, validation harness, README. Accept 14, or cut scope?
      Resolution: Budget 14 parts. (human, 2026-11-25) Raised to 16 for the R-4 and R-5 fixes. (human, 2026-11-26)
- A15. Q: The in-work project was read in full. Adopt its findings as proposed: U17 to U20, strengthened U2 to U15, K10 on a new `risk.mutates_data` flag, a guardrails section, new templates, gate examples and a deferral-marker hook, plus the practices it does well?
      Resolution: Approved as proposed, with its good practices added as well. It is referenced only as "the in-work project". (human, 2026-11-27)
- A16. Q: Make the method checkable by outsiders: CI on Linux and Windows running every gate that needs no local data with its control, a git pre-commit form of the deferral hook for people not on Claude Code, and the 2 defects (R-6, R-7) a fresh-clone run found. This takes 4 parts; raise the budget from 16 to 20?
      Resolution: Approved; budget 20. (human, 2026-11-27)
- A17. Q: An outside review of chrysalis.py found 3 defects (R-8 worktree base ignores repo.default_branch, R-9 table rows split on pipes inside cells, R-10 silent folder-depth limit). Each fix is a rework part; raise the budget from 20 to 23?
      Resolution: Approved; budget 23. (human, 2026-11-27)
- A18. Q: U21 (one promise, every member) applied to R-8 found R-11: `lusser parts` still defaults to main and ignores repo.default_branch. The fix is a rework part; raise the budget from 23 to 24?
      Resolution: Approved; budget 24. (human, 2026-11-27)
- A19. Q: An outside review (2026-11-28) found the method heavier than small work needs, its deferral rule too absolute, its enforcement narrower than its rules, and its tooling tied to Claude Code. Plan: grade every rule (control, scaled, practice) with change classes C0 to C2 and a `classify` command; register states SCHEDULED and ACCEPTED, with markers that cite a row; a `doctor` compliance check with a CI template and an enforcement map; AGENTS.md, a hook adapter, a pre-commit hook, `skills install` and a pilot guide. That is 10 parts; raise the budget from 24 to 34?
      Resolution: Approved; budget 34; commit and push once every suite and CI pass. (human, 2026-11-28) Raised to 35 when the config keys were counted as their own part. (human, 2026-11-28)
- A20. Q: U10 says lusser applies to all work regardless of size (decided 2026-11-25). Scale it by class: C0 needs no spec, only the claim and its check in the commit; C1 a minimal spec; C2 a full spec?
      Resolution: Scale U10 by class as proposed. (human, 2026-11-28)
- A21. Q: scripts/chrysalis.py reached 1,341 lines against U9's limit of about 500 (R-12). Fix it now by splitting it, and the test file it led to, by responsibility?
      Resolution: "Refactor that and split it up properly and logically." Budget 36 for the split as one rework part. (human, 2026-11-28)
