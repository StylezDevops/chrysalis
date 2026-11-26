# Domain sweep class lists

Use when no installed checklist skill covers the domain. Walk in order; mark each checked / N/A / finding. Combine sets where a project spans domains. Prefer an installed domain skill when one exists (e.g. `audio-plugin-audit all` for JUCE/VST; `adversarial-assurance` for security-heavy changes).

## audio-dsp
rt-safety → threading → denormals → sample-rate/block-size → channels → parameter smoothing → dsp correctness → state save/restore → lifetime → undefined behaviour

## web-frontend
rendering/hydration → state & effects (stale closures, missing deps) → async races (unmounted updates, out-of-order responses) → input validation & XSS → auth/session handling in client → accessibility → error & loading states → caching/invalidation → memory leaks (listeners, intervals) → bundle/perf regressions

## web-backend
input validation → authn/authz (IDOR, missing checks) → injection (SQL, command, template, SSRF) → transactions & idempotency → concurrency (double-submit, lost update) → error handling & leakage → resource lifetime (connections, file handles) → timeouts/retries → pagination & limits → logging of secrets → config/env assumptions

## data
schema assumptions → nulls/empties → type coercion & precision → timezone/DST → dedupe & keys → late/out-of-order data → partial failure & reruns (idempotency) → volume/skew → PII handling

## infra
least privilege → network exposure → secrets handling → state/drift → destroy/replace side effects → quotas/limits → region/zone assumptions → rollback path → observability

## mobile
lifecycle (background/foreground, process death) → threading (main-thread work) → permissions → offline/flaky network → storage & migrations → locale/RTL → memory → deep links & input validation

## library
public API contract → backwards compatibility → error types → thread safety claims → resource ownership → platform/version matrix → undefined/implementation-defined behaviour → docs vs behaviour

## concurrency (add to any set when relevant)
shared mutable state → lock ordering → atomicity of check-then-act → cancellation → backpressure → starvation → ABA / lifetime across threads
