# TypeScript, where to dig

**Runtime/type mismatches**: The type system stops at the boundary. Anything from `fetch`, `JSON.parse`, `req.body`, env vars, DB rows, or `localStorage` is `any` in a type costume. Look for casts (`as Foo`) without runtime checks, missing `zod`/`io-ts`/`valibot` at ingress, `!` non-null assertions on external data, optional chaining that hides missing-data bugs instead of surfacing them.

**Authentication flows**: Token storage (localStorage vs httpOnly cookie), token expiry and refresh races, CSRF on cookie-auth endpoints, `redirect` params without allowlisting, session fixation, OAuth `state` not validated, JWT `alg` not pinned, secrets in client bundles (check `NEXT_PUBLIC_`, `VITE_` prefixes).

**API contracts**: Client and server types that drifted; response shapes assumed but not validated; error responses not typed so the client treats a 500 body as success; pagination and versioning assumptions; endpoints that accept more fields than they should (mass assignment via spread).

**State management**: Stale closures in hooks; effects that run more than intended; derived state stored instead of computed; optimistic updates without rollback; global stores mutated outside reducers; race between two in-flight requests resolving out of order and the later-started one losing.

**Client/server trust assumptions**: Any check that exists only in the UI (disabled buttons, hidden routes, client-side role checks). Server handlers must be reviewed as if the client is hostile: does the server re-derive user ID from the session, or trust `userId` in the body? Are prices, quantities, permissions sent from the client and used as-is?

**Also common**: Prototype pollution via deep merge on user objects; `eval`-adjacent APIs (`new Function`, `innerHTML`, `dangerouslySetInnerHTML`); unhandled promise rejections; `await` missing so errors escape `try`; Node `child_process` with string commands; path traversal in file-serving routes; SSRF via user-supplied URLs.

**Tools E should reach for**: `tsc --noEmit --strict`, `eslint` with `@typescript-eslint` and security plugins, `semgrep --config p/typescript`, `npm audit` / `pnpm audit`, `fast-check` for property tests, the project's test runner (`vitest`/`jest`/`playwright`).
