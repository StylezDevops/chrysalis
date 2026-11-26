# A number through the shipping path

The rule: the measurement exercises what ships, produces a number (or a pass/fail derived from one), and moves when the defect is armed.

| Domain | Shipping path | Example numbers |
|---|---|---|
| Audio / DSP | Built plugin/CLI rendering real buffers at host-like block sizes and sample rates | peak/RMS delta vs reference, NaN/Inf count, denormal CPU time, allocations on audio thread, xrun count, latency samples |
| Web frontend | Production build served and driven by a real browser (Playwright/Cypress) | failing assertion count, console errors, CLS/LCP, a11y violation count, bundle bytes, network request count |
| Web backend / API | Running server over HTTP against a real (test) DB | status code distribution, p95 latency, rows written/leaked, duplicate count under concurrency, error rate |
| Data / ETL | The pipeline job as deployed, on a fixture dataset | row count delta, null count, checksum mismatch, dedupe violations, schema drift count |
| Infra / IaC | Plan/apply against an ephemeral environment | drift count, resources with public exposure, policy violations, reconcile loops |
| Mobile | Release build on emulator/device | crash count, ANR count, frame drops, memory high-water |
| Library / SDK | Packed artefact installed into a consumer fixture | failing consumer tests, API surface diff, perf ns/op |
| Concurrency | Real threads/processes, stress-looped | race detector hits, failures per N iterations, deadlock timeouts |

**Anti-patterns** (measurement that isn't): a unit test that mocks the thing that's broken; a debug build when the defect is release-only; a single-threaded run of a race; asserting "no exception" when the defect is wrong output; a test that passes with the fix reverted.

**Positive control recipes:** revert the fix in a scratch branch; env-var fault hook compiled into test builds only; fixture that reproduces the bad input; mutation of the guarded line. Record armed and disarmed values side by side.
