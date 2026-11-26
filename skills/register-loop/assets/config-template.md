# register-loop config
<!-- Lives at .claude/register-loop.md. Everything project-specific goes here; the loop itself stays generic. -->

## Register
- path: docs/AUDIT_REGISTER.md
- row states: OPEN / IN PROGRESS / DONE / QUEUED / REJECTED
- row id format: e.g. R-042
- evidence columns: baseline, armed, fixed, test, commit

## Shipping path
<!-- What real users/callers exercise. The measurement must go through this. -->
- artefact/entry point: e.g. release VST3 via the project CLI | `npm run build && npm start` on :3000 | release binary | deployed Helm chart via kind
- how to measure: e.g. CLI render + RMS/peak diff | Playwright/HTTP probe + status/latency/row count | benchmark harness | kubectl + metric

## Fault injection (positive control)
- mechanism: e.g. `INJECT=<row-id>` env var | feature flag | `git stash` of the fix | fixture swap | mutation
- red-then-green command: e.g. `scripts/inject.sh <row-id>`

## Green gate (all must pass)
- e.g. ci_local.bat
- e.g. ci_wsl.sh
- e.g. unit suite command
- row injection red-then-green

## Subagent isolation
- audit_model: most capable available (e.g. Opus 5)
- isolation: e.g. `BUILD_DIR=build-audit` | separate git worktree | `PORT=3100` + `DATABASE_URL=...audit` | own docker compose project name
- forbidden: e.g. ci_local.bat | `docker compose down -v` | `terraform apply` | anything touching shared state

## Warn-before commands
<!-- Things you run that would confuse the subagent. It gets a heads-up message first. -->
- e.g. ci_local.bat, opens with a machine-wide `taskkill /F /IM <app>.exe`
- e.g. `npm run db:reset`, drops the dev database

## Domain sweep
- skill: e.g. `audio-plugin-audit` with `all` | `adversarial-assurance` | none
- or classes: pick a set from references/sweeps.md (web-frontend, web-backend, data, infra, mobile, library, concurrency)
- extra project-specific classes: ...

## Budget and handover
- context threshold: 85%
- handover path: docs/HANDOVER.md
