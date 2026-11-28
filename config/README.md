# config_project.json

One file per project, at the project root. `chrysalis.py validate --config config_project.json` checks
it; every gap or contradiction comes back as a numbered question, and `apply` refuses to run until
there are none. The fields are the ones the method actually branches on; nothing is collected for its
own sake.

| Field | Type | Required | Used for |
|---|---|---|---|
| `schema_version` | integer | yes | the config's own version; `config migrate` moves an older one up |
| `project.name` | string | yes | file titles |
| `project.title` | string | no | display name; defaults to the name |
| `project.description` | string | yes | `initial.md`, `CLAUDE.md` |
| `project.problem` | string | yes | `initial.md` |
| `project.users` | list of strings | yes | `initial.md` |
| `project.objectives` | list of strings | no | `initial.md` |
| `stage` | `new`, `pre-release` or `live` | yes | K2 (no compatibility code before release) |
| `repo.existing` | bool | yes | contradiction check against `stage` |
| `repo.default_branch` | string | no | worktree base |
| `stack.languages` | list of strings | yes | `initial.md`, `CLAUDE.md` |
| `stack.frameworks` | list of strings | no | `initial.md` |
| `stack.platforms` | list of strings | no | K6 when it contains `web` |
| `risk.live_production` | bool | yes | K1, K3, K9 |
| `risk.handles_money` | bool | yes | K4 |
| `risk.handles_personal_data` | bool | yes | K4 |
| `risk.auth` | bool | yes | K4 |
| `risk.realtime` | bool | yes | K5 |
| `risk.client_engagement` | bool | yes | K8 |
| `risk.mutates_data` | bool | yes | K10: the software writes, deletes or syncs data it does not wholly own; K12 |
| `risk.infrastructure` | bool | yes | K11: the project changes infrastructure (Terraform, Bicep, ARM, Kubernetes, containers, network, identity, secrets) |
| `ci.remote` | `none`, `on-request` or `every-push` | yes | K7 |
| `ci.local_gate` | string | no | the command shown in `CLAUDE.md` and the gates template |
| `agents.max_parallel_agents` | integer 1 to 8 | yes | U16 cap |
| `framework.path` | string | no | where generated files point for the framework; defaults to `${CHRYSALIS_HOME}` |
| `framework.ref` | 40-character commit SHA | no | the framework commit the generated CI workflow pins; defaults to this checkout's commit |
| `change.critical_paths` | list of globs | yes when auth, money, personal data or data changes are flagged | changes to these paths are C2 |
| `change.small_lines` | integer 1 to 500 | no | the most changed lines a C0 change may have (default 20) |
| `adapt` | list of adaptations | no | scaled rules and practices adapted with a human decision and a revisit date (see PROPORTION.md) |
| `markers.exempt` | list of globs | no | files that hold deferral-marker words as data; doctor counts them |
| `notes` | string | no | free text, not read by the tools |

The risk flags have no defaults on purpose: each one is a decision about the project, so leaving one out
is a question, not a silent `false`.

Contradictions the validator refuses:

- `stage` is `new` but `repo.existing` is true;
- `stage` is `live` but `risk.live_production` is false, or the reverse;
- `agents.max_parallel_agents` outside 1 to 8;
- any field not in the table above (usually a typo).

Each problem has a kind. Invalid (a wrong type, an unknown field, a contradiction, a schema this Chrysalis cannot read) and incomplete (a decision not made yet) block `validate` and `apply`. Dangerous (valid but risky: a live system with no remote CI, a broad marker exemption, a very large C0 limit, an absolute framework path, more than 4 parallel agents) and deprecated are printed as warnings every time and do not block.

`config_project.example.json` is a filled example for a real-time audio plugin.
