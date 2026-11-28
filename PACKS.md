# Control packs

Conditional rules for kinds of change that carry risks of their own. They work like the K rules in
`METHOD.md`: each names the config that puts it in force, `chrysalis.py rules` selects it, and each
cites the defects it came from. They live here so `METHOD.md` stays short enough to read every session.

| ID | Applies when (config) | Rule | Evidence |
|---|---|---|---|
| K11 | `risk.infrastructure` | An infrastructure change (Terraform, Bicep, ARM templates, Kubernetes manifests or Helm charts, container images, network policy, identity and access, secrets) is C2 and leaves a record of eight steps in `docs/standards/infra-change.md`: (1) the planned difference captured from the tool (`terraform plan`, `az deployment what-if`, `kubectl diff --server-side`); (2) the files checked by their own validator and by policy as code, each policy shown catching a planted violation by its finding ID; (3) a security review of every identity, network and secret change; (4) the blast radius named, as a K1 class when live; (5) a human's approval recorded; (6) the deploy; (7) verification against the running target, not the manifest; (8) rollback performed, not described. A manifest checked only as data is not verified: it runs first on a throwaway cluster or environment. | Substrate internal AUDIT_REGISTER R-148 (an egress NetworkPolicy the code relied on did not bound SSRF), R-187 (it refused no IPv6 range), R-219 (ingress timeouts ended long writes), R-245 (left blocked because no controller was run); Substrate services/api/tests/test_infra_networkpolicy.py; chrysalis tests/infra_sim.py |
| K12 | `risk.mutates_data` or `risk.live_production` | A schema migration is tested on the database engine production runs, started for the test, never a stand-in: it applies to an empty database, applies a second time without error or change, reverses, and applies again to the same schema. | Substrate internal AUDIT_REGISTER R-059 (a Postgres URL that could not connect silently became SQLite); chrysalis tests/infra_sim.py migration run |

Each pack's simulation is `tests/infra_sim.py`: it runs the validators and policies against good and
planted-bad fixtures, deploys to a throwaway Kubernetes cluster in Docker, verifies the running
service, rolls a broken release back, and runs a migration up, up, down and up on a real database.
