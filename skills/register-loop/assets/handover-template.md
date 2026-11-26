# Handover, <project>, <date>

## Loop (authoritative, run exactly this)
<!-- Paste the loop verbatim as confirmed with the user this session, filled in from config, including any amendments. Do not summarise. -->

1. Next OPEN row in <register path> order, one row, no batching.
2. Measure the defect as a number through the shipping path (<how>), then positive-control the detector (arm via <mechanism>, confirm the measurement moves). A measurement that passes with the defect armed is measuring something else.
3. Fix, plus a test that fails if the behaviour regresses.
4. Green on <gate 1>, <gate 2>, <suites>, and the row's own injection red-then-green.
5. Adversarial audit: <model> subagent, fresh context, own <isolation>, forbidden <commands>. It runs <sweep> as its systematic pass over the touched code, then the free-form adversarial brief on top, because the checklist does not contain the unknown bug classes. Two messages to it, both earned: a warning before <warn-before command> (<why>), and "audit the fixes" afterwards, that is where the findings are.
6. Verify each finding as a failing number before acting; fix or queue with a row number. Audit the fixes again; repeat until a round comes back clean.
7. Green again, commit, push, next row.
8. At ~<threshold>% context, stop taking rows and write the handover.

## State
- Last completed row: <id> (<commit>)
- Current row: <id>, <status: not started / measured / fixed / in audit round N / parked>
- If parked: exactly what's done, what's next, any uncommitted work and where it is
- Next OPEN rows: <id>, <id>, <id>

## Rows closed this session
| Row | Baseline | Armed | Fixed | Test | Commit | Audit rounds |
|-----|----------|-------|-------|------|--------|--------------|

## Rows queued this session
| New row | Found during | One-line description |
|---------|--------------|----------------------|

## Rejected findings
| Finding | Reproduction attempted | Why rejected |
|---------|------------------------|--------------|

## Environment gotchas learned
<!-- Flaky gates, machine-wide side effects, ordering traps. Things the next session would otherwise rediscover the hard way. -->
