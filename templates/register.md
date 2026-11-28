# {{title}}: defect register

One row per defect (U3). Rows are never renumbered or deleted. A finding becomes a row only once it is
reproduced; otherwise it is a 1-line note under "Unreproduced".

Columns:

- **Measure**: what number shows the defect, and through which path.
- **Before / After**: the measured values. A CLOSED row needs both, and they must differ.
- **Test**: path to the regression test that fails without the fix.
- **State**: OPEN, CLOSED, SCHEDULED or ACCEPTED (U6). Nothing else is accepted.
- **Follow-up** for a CLOSED row: the decision on what else the defect becomes. Start with `gate:`,
  `rule:`, `adr:`, `bug-class:` or `none:` followed by the reason.
- **Follow-up** for a SCHEDULED row: `scheduled: OWNER, due YYYY-MM-DD, reason`.
- **Follow-up** for an ACCEPTED row: `accepted: NAME (human, YYYY-MM-DD), revisit YYYY-MM-DD, reason`.
  Only a human records it.

`chrysalis.py register check` fails on a row missing these, and on a due or revisit date that has
passed. `--release` also fails on any OPEN row. A marker in code cites its row ID in brackets, such as
`(R-12)`, on the marker's line.

| ID | State | Defect | Measure | Before | After | Test | Follow-up |
|---|---|---|---|---|---|---|---|

## Unreproduced

- (none yet)
