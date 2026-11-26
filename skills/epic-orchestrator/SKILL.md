---
name: epic-orchestrator
description: Take a described epic, feature, task, application, or piece of software; break it into dependency-ordered chunks; and orchestrate a team of siloed subagents to build it in parallel without stepping on each other. Use this whenever the user describes something to build that is bigger than one sitting, "build me a...", "implement this feature", "here's the epic", "I need an app that...", "split this up and get it done", "use N agents to...", even if they don't say "orchestrate", "plan", or "subagents". Also use when the user asks to plan or break down a large piece of work, or to run parallel agents on a codebase. Each subagent gets only its own brief, interfaces, and the project rules, never the whole epic.
---

# Epic Orchestrator

You are the one agent that sees the whole picture. Everyone you spawn sees a slice. Your job is to cut the slices well, hand each one to a builder with exactly what it needs and nothing it doesn't, and stitch what comes back into a working whole.

Why the silo matters: a subagent given the full epic will drift, it optimises for the story it understands rather than the chunk it was asked for, touches files it shouldn't, and makes decisions that belong to you. A subagent given a tight brief, clear interfaces, and the project rules builds the thing in front of it and reports back. That's the contract.

Why waves rather than live management: subagents run to completion and return. You can't feed one mid-task. So the work moves in waves, dispatch what's unblocked, read what returns, update the shared contracts, cut the next briefs from that. A silo can be re-dispatched with follow-up work; it keeps its worktree and its history.

## Workspace

Everything lives in `.orchestra/<epic-slug>/`, gitignored (append `.orchestra/` to `.gitignore` if missing):

```
.orchestra/<epic-slug>/
├── intake.md          # the user's description + answers to intake questions
├── rules.md           # snapshot: CLAUDE.md + user's extra constraints (what every silo gets)
├── PLAN.md            # chunks, dependencies, waves, mermaid graph, the gated artefact
├── contracts.md       # interfaces between chunks; grows as silos report back
├── log.md             # dispatch/return/merge events with timestamps
├── silos/<chunk-id>/
│   ├── brief.md       # exactly what that subagent was given
│   └── report-<n>.md  # exactly what it returned (n increments on re-dispatch)
└── worktrees/<chunk-id>/   # git worktrees (git repos only)
```

## Step 1, Intake

Read the user's description, then `CLAUDE.md` (root and any nested ones) and the repo layout. Then ask the intake questions in `references/intake-questions.md`, all at once, not one at a time. The two you always need: **how many agents may run concurrently**, and **any rules beyond CLAUDE.md** that builders must follow. Write everything to `intake.md` and build `rules.md` from CLAUDE.md plus the extras. Don't proceed until you have a concurrency number.

## Step 2, Decompose

Follow `references/decomposition.md`. The output is `PLAN.md` using `assets/plan-template.md`: chunks with IDs, acceptance criteria, owned paths, dependencies, wave assignment, and a mermaid dependency graph. Seed `contracts.md` with every interface that crosses a chunk boundary, signatures, schemas, routes, events, because those are the seams and they need to be agreed before anyone builds against them.

Sizing rule of thumb: a chunk is one subagent session, something a focused engineer finishes in a sitting with a clear "done". Too big and the silo starts making architecture decisions; too small and you spend the run on merges.

## Step 3, Gate

Show the user `PLAN.md` in full, chunks, dependencies, waves, the graph, the contracts you've assumed, and stop. Nothing is spawned until they approve. Fold their changes back into the plan and contracts and show it again if the changes were material.

## Step 4, Run waves

Loop until every chunk is done or blocked:

1. **Select**: chunks whose dependencies are all `merged`, up to the concurrency limit. Prefer chunks that unblock the most others.
2. **Isolate**: git repo: `git worktree add .orchestra/<slug>/worktrees/<id> -b epic/<slug>/<id> <integration-branch>`. Not git: shared tree, and the brief's owned-paths list becomes a hard boundary; run one wave at a time if chunks would build in the same tree.
3. **Brief**: write `silos/<id>/brief.md` from `references/silo-brief.md`. The brief carries the chunk's goal and acceptance criteria, its owned paths, the interfaces it must expose and may consume (copied from `contracts.md`, signatures only, never other chunks' implementations), `rules.md` verbatim, and the report format. It does not carry the epic narrative, the other chunks, or your reasoning. If a builder would need to know something to do its job, put it in; if it would merely be interesting, leave it out.
4. **Dispatch**: spawn all selected chunks in the same turn. Log it.
5. **Receive**: each returns a report in the shape of `references/completion-report.md`. Before merging, check it: did it stay inside its owned paths? Did it implement the interfaces as contracted, or deviate? Did its tests run and pass? If it strayed or its interfaces drifted, re-dispatch the same silo with a correction brief rather than fixing it yourself, you stay orchestrator, not builder.
6. **Merge**: in the worktree run the project's tests; then merge `epic/<slug>/<id>` into the integration branch; run tests again on the integration branch. Conflicts should be rare given path ownership; if one appears, it means two chunks touched one file, resolve it, and note in `log.md` that the plan had a boundary error.
7. **Propagate**: update `contracts.md` with the *actual* exposed interfaces from the report (they're now truth). Anything a report flags as "another chunk needs to know this" goes into the relevant dependent's brief when it's cut. Anything flagged as a question you can't answer from the plan goes to the user before that dependent is dispatched.
8. Mark the chunk `merged`, unblock dependents, go to 1.

Give the user a short update at the end of each wave: what merged, what's dispatched next, anything that needs their call.

## Step 5, Finish

When the graph is exhausted: run the full test suite on the integration branch, walk the epic's original acceptance criteria against what was built, and report gaps. Leave the integration branch for the user to review and PR, don't merge to their main branch. Offer to remove the worktrees (`git worktree remove`) once they've looked.

Final chat report: chunks completed, re-dispatches and why, contract changes from plan to reality, open questions, integration test results, branch name.

## Things that go wrong

- **A silo asks to see more of the project.** Usually a sign the brief was thin, not that the silo should see everything. Answer the specific question in a re-dispatch; don't widen the silo.
- **A silo reports a better architecture.** Read it. If it's right and contained, accept and update contracts. If it affects other chunks, stop and take it to the user, that's a plan change, not a silo decision.
- **Two chunks want the same file.** Split the file's ownership explicitly, or merge the chunks, or serialise them. Never let two live silos own one path.
- **Concurrency limit hit with everything blocked.** The graph has a cycle or a chunk is too big. Go back to the plan, tell the user.
- **Tests don't exist.** Say so at intake. Ask whether builders should write them (recommended, the completion report needs evidence) and put the answer in `rules.md`.
