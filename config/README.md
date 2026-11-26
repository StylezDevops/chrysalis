# config_project.json

One file per project, at the project root. `chrysalis.py validate --config config_project.json` checks
it; every gap or contradiction comes back as a numbered question, and `apply` refuses to run until
there are none. The fields are the ones the method actually branches on; nothing is collected for its
own sake.

| Field | Type | Required | Used for |
|---|---|---|---|
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
| `ci.remote` | `none`, `on-request` or `every-push` | yes | K7 |
| `ci.local_gate` | string | no | the command shown in `CLAUDE.md` and the gates template |
| `agents.max_parallel_agents` | integer 1 to 8 | yes | U16 cap |
| `framework.path` | string | no | where generated files point for METHOD.md; defaults to this repo |
| `notes` | string | no | free text, not read by the tools |

The risk flags have no defaults on purpose: each one is a decision about the project, so leaving one out
is a question, not a silent `false`.

Contradictions the validator refuses:

- `stage` is `new` but `repo.existing` is true;
- `stage` is `live` but `risk.live_production` is false, or the reverse;
- `agents.max_parallel_agents` outside 1 to 8;
- any field not in the table above (usually a typo).

`config_project.example.json` is a filled example for a real-time audio plugin.
