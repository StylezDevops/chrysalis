# Completion report

The builder returns this. The orchestrator reads it to merge, to update contracts, and to brief dependents. Every section is required; "none" is a valid answer.

```markdown
# Report, <chunk-id>, dispatch <n>

## Status
Done / Partial / Blocked

## What was built
<short, concrete. Files created, components implemented, behaviour delivered against each acceptance criterion.>

## Files touched
<full list. The orchestrator checks this against owned paths.>

## Interfaces exposed, actual
<every interface from "must expose", with the real signature as implemented. If identical to the brief say "as specified". If different, show both and say why.>

## Deviations from brief
<anything done differently from what was asked, and the reason>

## Assumptions made
<decisions taken where the brief was silent. These are the things the orchestrator most needs to see.>

## Tests
<what was run, command, result. Paste the summary line. If no tests: why.>

## Things a downstream builder needs to know
<gotchas, ordering requirements, config that must be set, behaviour that isn't obvious from the signature. Written for someone who will never see this chunk's code.>

## Blocked / needs orchestrator
<questions that can't be answered from the brief; requests to touch paths outside ownership; conflicts with the rules. Leave empty if none.>
```

## What the orchestrator does with it

| Section | Action |
|---|---|
| Files touched | Compare to `owns`. Outside → re-dispatch with correction, don't merge |
| Interfaces, actual | Replace `proposed` with `actual` in contracts.md. If changed, check which dependents consume it and adjust their pending briefs |
| Deviations / Assumptions | Judge each: fine, needs a correction re-dispatch, or needs the user |
| Tests | No evidence → no merge. Re-dispatch asking for it |
| Downstream needs to know | Copy into the relevant dependents' briefs |
| Blocked | Answer in a re-dispatch if it's answerable from the plan; otherwise take it to the user before continuing that branch of the graph |
