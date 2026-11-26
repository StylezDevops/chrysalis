# .lusser/ file formats

All three files are plain text. The checker (`scripts/lusser.py`) parses exactly the shapes below; anything else in the files is ignored, so add prose freely.

## spec.md

```markdown
# Spec: <short title>

Budget: 12 parts
Assumed p: 0.95

## Clauses

- C1. <one testable statement of behaviour>
- C2. [critical] <clause touching money / migration / auth / destructive ops>
- C3. <...>

## Ambiguities

- A1. Q: <the two readings, concretely>
      Resolution: <what the human decided> (<who>, <date>)
- A2. Q: <...>
      Resolution: OPEN
```

Rules the checker reads:

- A clause is a line starting `- C<n>.`; `[critical]` immediately after the number marks it critical.
- An ambiguity is a line starting `- A<n>. Q:`. The next line starting `Resolution:` (any indentation) is its resolution. `OPEN`, `TBD`, or a missing resolution line fails the check.
- `Budget:` and `Assumed p:` may appear anywhere. Defaults: no budget (warns), p = 0.95.

## parts.md

```markdown
# Parts ledger

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | fast-check 3.x | dependency | property tests for C2/C4 | yes, 2018+, ~5M weekly downloads, active |
| 2 | POST /checkout/total | interface | new endpoint per C1 | no |
| 3 | orders.discount_code column | schema-change | C3 | no |
| 4 | Stripe Tax API | external-api | C2, replaces bespoke tax table | yes, vendor-maintained |
| 5 | fix: rounding on C2 after property test failure | rework | | no |
```

Rules:

- Any markdown table row whose first cell is an integer is a part. Column order is fixed: `#`, `Part`, `Kind`, `Justification`, `Proven`.
- Kind is one of: `dependency`, `external-api`, `schema-change`, `module`, `interface`, `config`, `handoff`, `rework`. Unknown kinds warn.
- `Proven` starts with `yes` to count as proven. The checker reports proven and unproven counts separately; both count toward the budget (a proven part is still a part), but the summary shows p^n for unproven parts alone as well, since that is where the risk sits.

## checks.toml

```toml
# One [[check]] table per check. A clause may have many.

[[check]]
clause = "C1"
kind   = "spec-test"
ref    = "tests/checkout.spec.ts"
note   = "written from C1 before implementation, commit a1b2c3"

[[check]]
clause = "C2"
kind   = "property"
ref    = "tests/checkout.property.spec.ts"

[[check]]
clause = "C2"
kind   = "real-input"
ref    = "fixtures/orders-2026-09.jsonl"
note   = "300 real orders exported from prod, PII stripped"

[[check]]
clause = "C3"
kind   = "human-accept"
ref    = "A. Patel, 2026-10-02"
note   = "walked through discount flow on staging"
```

Rules:

- `kind` is one of `model-review`, `model-test`, `spec-test`, `property`, `differential`, `real-input`, `human-accept`.
- For `spec-test`, `property`, `real-input`, `differential`: if `ref` contains a `/` or `\` or ends in a known file extension, the path (before any `::` or `#`) must exist relative to the repo root.
- `human-accept` refs are free text. The checker cannot verify them. Do not write one that a human did not give you.

## escapes.md

Append-only. One entry per production defect.

```markdown
## 2026-10-14, discount applied twice on retry
- Clause: C3
- Parts: #2 interface, #5 rework
- Checks that covered C3: spec-test, human-accept
- What they missed and why: acceptance used a single submit; retry path never exercised. Add real-input replay of double-submits.
```
