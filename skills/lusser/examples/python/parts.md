# Parts ledger

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | stripe (official Python SDK) | dependency | C1, C5, includes built-in retries and pagination; bespoke HTTP client rejected | yes, vendor-maintained, 2011+ |
| 2 | Stripe Payouts + BalanceTransactions API | external-api | C1, C2 | yes |
| 3 | reconcile CLI (argparse, stdlib) | interface | C1; click/typer rejected, one command, two flags | no |
| 4 | csv + decimal (stdlib) | module | C3, C4, C6, no pandas; two output files | yes, stdlib |
| 5 | hypothesis | dependency | property tests for C2/C3/C4, dev-only | yes, 2013+, active |
| 6 | vcrpy | dependency | records real Stripe responses for real-input tests, dev-only | yes, 2012+, active |
