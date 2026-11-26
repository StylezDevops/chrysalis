# Silo brief

This is what a builder subagent receives. Nothing else. Write it as a self-contained document, the builder has no access to PLAN.md, intake.md, other silos, or the orchestrator's reasoning.

The test for every line: does the builder need this to build its chunk correctly and stay in its lane? If yes, include it. If it's context that would help the builder "understand the project", leave it out, that understanding is what makes silos wander.

```markdown
# Build brief, <chunk-id>: <title>

You are building one component of a larger piece of work. You will not be told what the larger work is, and you don't need to know. Build what's described here, inside the boundaries given, and report back in the format at the end.

## Goal
<one paragraph, what this chunk does and why it exists, in terms of its own behaviour>

## Acceptance criteria
- <concrete, testable, scoped to this chunk>
- ...

## Where you work
- Repository root: <path, the worktree, or the shared tree>
- Branch: <epic/<slug>/<id>> (already checked out), or "shared tree, no branch"
- You own these paths and may create or modify anything under them:
  - <path>
  - <path>
- You must not modify anything outside those paths. If you believe you need to, stop and say so in your report under "Blocked / needs orchestrator", don't do it.

## Interfaces you must expose
<copied from contracts.md, proposed versions. Exact signatures. Say: "Implement these exactly as written. If you must deviate, do so and record the deviation in your report, a downstream builder will be given your actual signature.">

## Interfaces you may consume
<copied from contracts.md, actual versions from merged chunks. Signatures and behaviour only, no implementation. If the chunk is running against a stub or contract-only, say so and tell the builder to code to the contract.>

## Rules
<rules.md verbatim>

## Testing
<what to run, what framework, what "passing" means for this chunk, from rules.md / intake>

## When you're done
Return a report in exactly this shape:
<paste references/completion-report.md body>
```

## Re-dispatch briefs

When sending a silo back (correction, follow-up, or new information from another chunk), keep the original brief and add a section at the top:

```markdown
## Update, dispatch <n>
<what changed: a correction to make, an interface that turned out different, a follow-up task. Be specific. Reference the previous report by name if disputing something in it.>
```

Same boundaries, same rules. The builder still doesn't get the wider picture.
