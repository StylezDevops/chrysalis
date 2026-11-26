# Decomposition

The goal is a set of chunks where each one can be built by a subagent that sees only its brief, and where the seams between chunks are written down before anyone builds.

## Method

1. **Extract acceptance criteria** from the description, the observable outcomes. Number them (AC1..n). Every chunk traces to at least one; every AC is covered by at least one chunk.

2. **Find the seams.** Look for boundaries that already exist or should: layers (data / domain / API / UI), services, modules, external integrations, cross-cutting concerns (auth, logging, config). A seam is a good chunk boundary when the two sides can be described to each other with an interface, a signature, a schema, a route, an event shape, rather than shared internals.

3. **Cut chunks along seams.** For each chunk record:
   - `id`, short, stable: `C1`, `C2`...
   - `title`
   - `goal`, one paragraph a builder can hold in its head
   - `acceptance`, the ACs it satisfies, restated concretely for this chunk
   - `owns`, paths (files or directories) this chunk may create or modify. Exclusive. If two chunks need the same path, fix the plan, not the rule.
   - `exposes`, interfaces others will consume, written into `contracts.md`
   - `consumes`, interfaces from other chunks, by contract ID
   - `depends_on`, chunk IDs that must be merged first
   - `size`, S / M / L. L is a smell; try to split.

4. **Check dependencies.** `depends_on` should be driven by `consumes` (needs a real implementation to build against) and by shared scaffolding (a chunk that creates the project skeleton comes first). Don't add dependencies for "it would be nice to see that first", that's the silo leaking. If a chunk only needs an interface, not an implementation, it can run in parallel against a stub or the contract alone; say which in the brief.

5. **Assign waves.** Wave 1 = chunks with no dependencies. Wave n = chunks whose dependencies are all in waves < n. The concurrency limit caps how many of a wave run at once; the orchestrator handles that at dispatch, so waves in the plan are about ordering, not batch size.

6. **Write contracts.** For every `exposes`, write the actual interface in `contracts.md`: language-level signature, request/response shape, table schema, event payload, CLI flags, whatever the seam is. Mark each `proposed`. When a silo reports back, replace with the real one and mark `actual`.

7. **Draw the graph.** Mermaid, in PLAN.md:
   ```mermaid
   graph LR
     C1[C1 skeleton] --> C2[C2 data layer]
     C1 --> C3[C3 auth]
     C2 --> C4[C4 API]
     C3 --> C4
   ```

## Sizing

A chunk is right-sized when a builder who reads only its brief could start immediately, would finish in one session, and would have no architecture decisions to make that affect anyone else. Signs it's too big: the brief needs a "background" section; it owns more than one layer; its acceptance list runs past six or seven items. Signs it's too small: its only real content is one interface; merging it costs more than building it.

## Cross-cutting chunks

Config, logging, error handling, shared types: either put them in the skeleton chunk (wave 1, everyone depends on it) or give them a contract everyone consumes. Don't let each silo invent its own, that's the most common source of integration pain.

## Non-git repos

Same method, but with no worktrees, path ownership is the only isolation. Be stricter about it and run chunks that share a build (same package, same compile step) in separate waves rather than in parallel.
