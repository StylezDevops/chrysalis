# Parts ledger

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | fastify | dependency | already the app framework | yes |
| 2 | zod | dependency | request schema (C1, C6, A2, A3); already in repo | yes, 2020+, very widely used |
| 3 | stripe (Node SDK), Tax Calculations API | external-api | tax per C5, replaces a bespoke VAT table | yes, vendor-maintained |
| 4 | POST /checkout/total | interface | C1 | no |
| 5 | src/checkout/money.ts (roundHalfUp, sum) | module | A1 rounding rule, ~30 lines; dinero.js considered, rejected as a whole dependency for two functions | no |
| 6 | discount_codes table read path | schema-change | C3/C4 read only; table already exists, new index on (code, expires_at) | no |
| 7 | fast-check | dependency | property tests, dev-only | yes, 2018+, active |
| 8 | STRIPE_TAX_ENABLED flag | config | allows C5 to fall back to 422 for all regions during rollout | no |
