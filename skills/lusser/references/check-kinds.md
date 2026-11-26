# Producing each check kind, per language

The point of a check kind is *how it fails*, not what tool it uses. Two checks of the same kind share blind spots; the rules in SKILL.md require at least one check per clause whose failure mode differs from a model reading or writing code.

## spec-test

A test written from the clause text, before or without seeing the implementation. Weakest of the "counts" kinds because a model still wrote it, it can misread the spec the same way the implementer did. That is why the ambiguity pass comes first and why a stronger kind is required alongside.

How to make it honest:
- Write and commit the test file before the implementation file. The commit order is the evidence; put the commit hash in `note`.
- In Claude Code, spawn a subagent with only `spec.md` in context and have it write the tests.
- Name each test after the clause: `test_C2_total_includes_tax`.

| Language | Framework |
|---|---|
| C++ | Catch2, GoogleTest, doctest |
| C#/.NET | xUnit, NUnit, MSTest |
| TypeScript | Vitest, Jest, node:test |
| Python | pytest, unittest |

## property

Generate many inputs from a description of the input space and assert an invariant. Finds inputs no one thought of. Especially good for anything numeric, parsing, encoding, ordering, or state machines.

Invariants worth stating: round-trips (`decode(encode(x)) == x`), idempotence (`f(f(x)) == f(x)`), monotonicity, conservation (totals before and after), commutativity where it should hold, and "never throws for valid input".

| Language | Library |
|---|---|
| C++ | RapidCheck; libFuzzer / AFL++ for fuzzing |
| C#/.NET | FsCheck (works from C#), CsCheck |
| TypeScript | fast-check |
| Python | Hypothesis; Atheris for fuzzing |

Seed the generator and record the seed on failure so the case is reproducible.

## differential

Run the same inputs through a reference, the old implementation, a vendor's calculator, a spreadsheet the accountant already trusts, a reference library in another language, and diff outputs. Strong because the reference was built by something with different blind spots.

Patterns:
- Old vs new during a migration or rewrite: shadow-run both, compare, log deltas.
- Bespoke vs proven: compare your implementation to the library you decided not to depend on (then ask why you aren't depending on it).
- Cross-language: the same algorithm in a second language rarely shares the same off-by-one.

Any language: a script that reads inputs, calls both, and writes a diff. Keep it stupid.

## real-input

Recorded real data or a real call to the external system. Strongest kind for the "looks right but does the wrong thing" fault, because real data carries the cases the spec forgot.

- Export a sample from production, strip personal data, commit it as a fixture, and replay it. Note the export date and row count.
- Record real API responses (VCR-style) rather than hand-writing mocks: `vcrpy` (Python), `nock` recorder / Polly.js (TS), `WireMock.Net` record mode (.NET), a captured JSON body in a fixtures directory (C++, no need for a library).
- For payment, messaging or auth providers: at least one test that hits the vendor sandbox for real, run in CI on a schedule if not on every push.
- For migrations: run against a restored copy of the real database, not a seeded one.

## human-accept

The person the work is for used it and said it does what they asked. The only check that can catch "we built the wrong thing well".

- Give them the clause list and ask them to tick each one they saw work.
- Record who and when in `ref`. Never fabricate this line.
- For internal tooling with no external user, the person who wrote the request counts.

## model-review and model-test

Still worth doing, they catch the cheap, obvious faults cheaply. They just do not count toward coverage on their own. Tag them honestly.
