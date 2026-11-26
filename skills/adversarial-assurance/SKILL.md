---
name: adversarial-assurance
description: Run an adversarial, evidence-driven software assurance review using six coordinated subagents (architect, contrarian, invariant analyst, verification planner, evidence collector, remediation architect). Use this whenever the user asks for a security review, code audit, assurance review, threat review, "poke holes in this", "what could go wrong", "is this safe to ship", a pre-merge risk review, or wants tests written to falsify assumptions about a PR, a component, or a whole repo, even if they don't say "adversarial" or "assurance". Produces a gitignored .assurance/ workspace with a findings report, generated tests, and collected evidence.
---

# Adversarial Assurance Review

The objective is not to approve software. It is to discover evidence that challenges assumptions about correctness, security, reliability, performance, maintainability, scalability, and business logic. Assume defects exist until sufficient evidence demonstrates otherwise.

This matters because reviewers, human and AI, drift toward confirmation: read the code, it looks plausible, sign off. This skill replaces "looks correct" with hypotheses that get tested, and replaces a single reviewer's judgement with six agents that are each told the previous agent is probably wrong.

## Core principles (every agent inherits these)

- Never trust a previous conclusion without verification.
- Never treat "looks correct" as evidence.
- Prefer evidence over reasoning; testing over speculation; falsification over confirmation.
- Challenge assumptions made by humans and by other agents.
- Document uncertainty explicitly.
- Focus on high-impact risks first.
- Don't stop at the first issue. Keep looking for alternative explanations and additional failure paths.

## Step 1, Resolve scope

The user may point at any of three scopes. Work out which from what they said; ask only if it's genuinely ambiguous.

| Signal | Scope | How to enumerate |
|---|---|---|
| "this PR", "the diff", "before I merge", or no target given on a feature branch | **Diff** | `git diff <base>...HEAD --name-only`; read full files, not just hunks, a hunk's danger usually lives in its callers |
| A path, module, service, or component name | **Component** | That path plus everything that calls into it or that it calls across a trust boundary |
| "the repo", "everything", "full audit" | **Whole repo** | Inventory first, then rank areas by blast radius (auth, money, data mutation, external I/O, privilege) and go deepest there |

Record the resolved scope and the base commit in `scope.md` so every agent works from the same target.

## Step 2, Create the workspace

All output lives in one directory so it can be gitignored and cleaned up in one move:

```
.assurance/<YYYYMMDD-HHMM>-<scope-slug>/
├── scope.md                    # resolved scope, base commit, files in scope
├── 01-architecture.md          # Agent A
├── 02-risk-hypotheses.md       # Agent B
├── 03-invariant-analysis.md    # Agent C
├── 04-verification-plan.md     # Agent D
├── 05-evidence.md              # Agent E
├── 06-remediation.md           # Agent F
├── tests/                      # generated tests, runnable in place
├── evidence/                   # logs, traces, tool output, coverage
└── REPORT.md                   # final assembled report
```

Add `.assurance/` to `.gitignore` if it isn't already there (append a line; don't rewrite the file). Tell the user you did this.

## Step 3, Detect stack and load guidance

Look at the files in scope and read the matching reference before spawning anyone, then pass the relevant reference path to each agent:

- `references/python.md`, input validation, serialization, dependency risk, async, resource exhaustion, privilege boundaries
- `references/typescript.md`, runtime/type mismatches, auth flows, API contracts, state management, client/server trust
- `references/solidity.md`, state transitions, economic incentives, access control, upgradeability, oracles, reentrancy, governance, value extraction

Mixed stacks load more than one. Unlisted stacks still get the generic review method below; note the gap in `scope.md`.

## Step 4, Run the agents

Each agent has its own brief in `agents/`. Spawn each as a subagent with: the brief file, `scope.md`, the stack reference(s), and the outputs of any agents it depends on. Every agent applies the same review method to every component in scope:

1. Identify assumptions
2. Identify trust boundaries
3. Identify privilege boundaries
4. Identify state transitions
5. Identify failure modes
6. Identify abuse cases
7. Identify unexpected interactions
8. Identify the evidence required to validate or invalidate each concern

**Phase 1, Agent A, System Architect** (`agents/a-architect.md`). Runs alone. Writes `01-architecture.md`: intended behaviour, design goals, trust model, critical business rules, invariants, assumptions. Everything downstream attacks this document, so it must be concrete, named functions, named boundaries, invariants stated as testable propositions.

**Phase 2, fan out B, C, D in parallel.** All three read `01-architecture.md`.

- **Agent B, Contrarian Reviewer** (`agents/b-contrarian.md`), assumes A is mistaken. Writes `02-risk-hypotheses.md`.
- **Agent C, Invariant Analyst** (`agents/c-invariant-analyst.md`), assumes the invariants will be violated. Writes `03-invariant-analysis.md`.
- **Agent D, Verification Planner** (`agents/d-verification-planner.md`), converts A's assumptions and invariants into tests. Writes `04-verification-plan.md` and the initial contents of `tests/`.

When B and C return, do a short reconciliation pass before Phase 3: read B and C's hypotheses against D's plan and spawn D again (briefly, with all three documents) to add tests for any hypothesis that isn't yet covered. Every hypothesis should map to at least one verification method or be explicitly marked "not testable here, needs X".

**Phase 3, Agent E, Evidence Collector** (`agents/e-evidence-collector.md`). Runs the tests in `tests/`, runs available static analysis, reads logs and traces, captures everything to `evidence/`. Writes `05-evidence.md` with three lists only: confirmed findings, rejected hypotheses, remaining unknowns. E reports nothing that isn't backed by an artefact in `evidence/`.

**Phase 4, Agent F, Remediation Architect** (`agents/f-remediation.md`). Takes confirmed findings only. Writes `06-remediation.md`: root cause, corrective design, regression tests to add, residual risk.

## Step 5, Assemble REPORT.md

Use `assets/report-template.md`. Every finding uses this exact block:

```
### <ID>, <short title>
**Observation**: what was discovered
**Evidence**: code references (path:line), logs, tests, traces, or tool output in evidence/
**Potential impact**: what happens if the issue exists
**Confidence**: High / Medium / Low
**Verification method**: how it was, or should be, validated
**Remediation**: recommended corrective action
```

Order findings by impact, then confidence. Rejected hypotheses get their own section, they're valuable because they record what was checked and how, so the next reviewer doesn't redo it.

## Termination condition

Never conclude the software is secure. The report ends with, and only with:

- Findings confirmed
- Findings rejected
- Areas not yet verified
- Recommended next verification steps

## Step 6, Report back in chat

Give the user a short summary: scope, counts (confirmed / rejected / unknown), the top three confirmed findings with confidence, the path to `REPORT.md`, and how to run the generated tests. Don't paste the whole report into chat, it's in the file.

## Practical notes

- Subagents should read the actual code, run the actual tests, and cite `path:line`. A finding without a location is a hypothesis, not a finding, send it back.
- If a test can't run in this environment (no network, missing toolchain, needs credentials), E records it under "remaining unknowns" with the exact command that would run it. Don't quietly downgrade it.
- Generated tests go in `tests/` inside the workspace, not the project's own test directory, unless the user asks. They use the project's existing test framework where one exists so they can be lifted across later.
- Time-box whole-repo reviews: if scope is large, say so up front and propose which areas get depth versus breadth before spawning agents.
