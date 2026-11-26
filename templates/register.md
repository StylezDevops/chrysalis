# {{title}}: defect register

One row per defect (U3). Rows are never renumbered or deleted. A finding becomes a row only once it is
reproduced; otherwise it is a 1-line note under "Unreproduced".

Columns:

- **Measure**: what number shows the defect, and through which path.
- **Before / After**: the measured values. A CLOSED row needs both, and they must differ.
- **Test**: path to the regression test that fails without the fix.
- **Follow-up**: the decision on what else the defect becomes. Start with `gate:`, `rule:`, `adr:`,
  `bug-class:` or `none:` followed by the reason.

`chrysalis.py register check` fails on any CLOSED row missing these.

| ID | State | Defect | Measure | Before | After | Test | Follow-up |
|---|---|---|---|---|---|---|---|

## Unreproduced

- (none yet)
