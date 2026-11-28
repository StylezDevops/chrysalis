# Infrastructure change: what, where, date

One record per infrastructure change (K11): Terraform, Bicep, ARM, Kubernetes manifests or Helm charts,
container images, network policy, identity and access, secrets. Each step links its evidence; a step
with no evidence is not done.

| Step | Evidence (link or attached output) | By | Date |
|---|---|---|---|
| 1. Planned difference captured from the tool (`terraform plan`, `az deployment what-if`, `kubectl diff --server-side`) | | | |
| 2. Validator and policy run; each policy's planted violation shown caught by finding ID | | | |
| 3. Security review of every identity, network and secret change | | | |
| 4. Blast radius named (K1 class when live) | | | |
| 5. Approval recorded: NAME (human, YYYY-MM-DD) | | | |
| 6. Deployed | | | |
| 7. Verified against the running target, not the manifest | | | |
| 8. Rollback performed on a throwaway environment, and the command that does it on this one | | | |

## What changes

Resources added, changed and removed, from the captured plan.

## What it can break

Who and what loses service, data or access if this goes wrong, and for how long.

## Rollback

The exact commands, and where they were last run.
