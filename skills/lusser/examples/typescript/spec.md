# Spec: Checkout total endpoint (Node 22, TypeScript, Fastify)

Context: the article's own example, a checkout page for an online store. This is the
server-side total calculation only. Prices are integer minor units (pence).

Budget: 9 parts
Assumed p: 0.95

## Clauses

- C1. POST /checkout/total accepts { items: [{sku, qty}], discountCode?, shipTo: {country, postcode} } and returns { subtotal, discount, tax, shipping, total } as integers in pence.
- C2. [critical] total == subtotal - discount + tax + shipping, with each component rounded independently to the nearest penny (half up) and summed; the result never differs from the payment provider's own computed amount for the same line items.
- C3. An unknown or expired discountCode returns 200 with discount = 0 and a `warnings: ["DISCOUNT_INVALID"]` field; it is not a 4xx.
- C4. A percentage discount applies to the subtotal only, never to tax or shipping; a fixed-amount discount cannot take subtotal below 0.
- C5. Tax is computed by the tax provider (not a local table) for GB; for any other country the endpoint returns 422 UNSUPPORTED_REGION.
- C6. Unknown SKUs return 422 with the offending SKUs listed; the response contains no partial totals.

## Ambiguities

- A1. Q: Round each line then sum, or sum then round? (They differ by up to n/2 pence.)
      Resolution: Round each *component* (subtotal, discount, tax, shipping) independently, then sum. Matches what Stripe shows on the invoice. (spec owner, 2026-09-30)
- A2. Q: Does a percentage discount apply before or after a fixed discount if both are somehow present?
      Resolution: Only one code per checkout; the schema rejects more than one. (spec owner, 2026-09-30)
- A3. Q: Is qty = 0 an error or a no-op line?
      Resolution: Error (422); the client should not send it. (spec owner, 2026-09-30)
