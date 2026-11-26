# Spec: Stripe payout reconciliation CLI (Python 3.12)

Context: a small label's bookkeeping. Match each Stripe payout to the sales that make it up
and produce a CSV the accountant imports. Money as Decimal, never float.

Budget: 7 parts
Assumed p: 0.95

## Clauses

- C1. `reconcile --from DATE --to DATE` fetches all payouts in the range and, for each, the balance transactions it comprises, and writes one CSV row per balance transaction with payout_id, arrival_date, type, gross, fee, net, currency, description.
- C2. [critical] For every payout, sum(net of its balance transactions) == payout.amount, to the penny; any payout where this does not hold is written to a separate `unmatched.csv` and the exit code is 2.
- C3. Amounts are written as decimal strings with exactly two decimal places for GBP (e.g. `123.40`), never in minor units and never in scientific notation.
- C4. Re-running over the same range produces a byte-identical CSV (deterministic ordering: arrival_date, payout_id, balance_transaction id).
- C5. Stripe rate limits (429) and transient 5xx are retried with backoff; after exhausting retries the tool exits 3 with no partial CSV written.
- C6. The CSV header row and column order match the accountant's import template exactly.

## Ambiguities

- A1. Q: "In the range", payout created date or arrival date?
      Resolution: arrival_date, because that is what appears on the bank statement the accountant reconciles against. (spec owner, 2026-09-30)
- A2. Q: Refunds and disputes appear as negative balance transactions, separate rows or netted into the sale row?
      Resolution: Separate rows, negative gross, type preserved. The accountant asked for this explicitly. (spec owner, 2026-09-30)
- A3. Q: Non-GBP payouts?
      Resolution: Out of scope; if any appear, they go to unmatched.csv with reason NON_GBP. (spec owner, 2026-09-30)
