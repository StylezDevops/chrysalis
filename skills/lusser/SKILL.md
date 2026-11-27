---
name: lusser
description: Reliability discipline for AI-built software, based on Lusser's product law (a project works only if every part works, so its odds are p^n). Use this whenever starting, scoping, planning or reviewing any coding task that adds code, dependencies, interfaces, migrations or agent handoffs to a project, in any language, even when the user only says "build", "add", "implement", "wire up", "migrate" or "review this PR". It forces three things the agent cannot do for itself, hold the part count down, resolve spec ambiguity with a human before building, and cover every spec clause with at least one check that fails differently from an agent (real inputs, property tests, differential runs, human acceptance). Also use when the user mentions Lusser, part budgets, spec clauses, check kinds, escaped defects, or asks whether a project "will actually work".
---

# Lusser

## Why this exists

A software change works only if every part of it works. Reliability is the product of the parts' reliabilities: fifty parts at 95% each work together 8% of the time; five hundred at 99% work together 0.7% of the time. Coding agents make parts almost free to add, so the count grows until the odds are indistinguishable from zero, and nothing points at a culprit, because every part performed about as well as it could.

Two things are known to make it worse: adding more agents, gates or reviewers (each is another part with the same blind spots), and squeezing the schedule so checking gets cut. Two things are known to help: **build less**, and **check what gets built with methods that fail differently from the agent**. An agent reviewing an agent, or an agent running tests an agent wrote after seeing the code, catches only the faults it would not have made itself. It misses the two hardest kinds: code that passes its tests and does the wrong thing, and a shared misreading of an ambiguous spec.

This skill cannot make you more careful. Its value comes entirely from routing decisions to things that are not you: a human resolving the spec, real data, mature software with a track record, and the person the thing is for.

## The three files

Every task governed by this skill has a `.lusser/` directory at the repo root with:

| File | What it holds | Who owns it |
|---|---|---|
| `spec.md` | Numbered clauses; ambiguities and their human resolutions; the part budget | Human resolves, agent drafts |
| `parts.md` | The ledger of every part the change adds, with a one-line justification each | Agent maintains, human reviews |
| `checks.toml` | Each clause mapped to the checks that cover it, tagged by kind | Agent maintains; `lusser check` enforces |

Plus `escapes.md`, appended to only when a defect is found after the work shipped. Formats are in `references/formats.md`. Worked examples for C++, TypeScript and Python are in `examples/`.

TOML is used (not YAML) so the checker runs on Python's standard library with zero dependencies. The checker is itself a part and must stay trivially small.

## Workflow

### 1. Scope: before any code

1. Turn the request into numbered clauses in `spec.md` (`C1`, `C2`…). A clause is one testable statement of behaviour, not a task. Mark clauses that touch money, data migration, auth, or destructive operations with `[critical]`.
2. List every ambiguity you can see, each point where two sensible readings split, as `A1`, `A2`… with a concrete question. Then **stop and ask the human**. Do not resolve them yourself, however obvious the answer seems: agents fail together precisely where the spec is ambiguous, and a wrong reading here is inherited by the code, the tests, and any reviewer. Work does not start with an unresolved ambiguity.
3. Agree a part budget with the human and write it into `spec.md`. If they don't have a number, propose one small enough that every part can get real checking (typically 5–15 for a feature-sized change) and explain that going over means stopping to ask, not pushing on.

### 2. Buy before build

Before writing any component, name the mature library, platform feature or existing internal code that could do the job, or state why none fits. Software in wide use has survived millions of runs from people with no stake in it working; that is the strongest check that fails differently from anything you can do. Record the decision in `parts.md`:

- A dependency counts as **proven** only with evidence: years in use, wide adoption, active maintenance. Note the evidence briefly.
- A young or niche dependency is an ordinary part, not a proven one, and it still needs a justification.
- Prefer one proven part over several bespoke ones. Prefer nothing over one.

### 3. Build: keep the ledger honest

Add a row to `parts.md` for every part the change introduces, as you introduce it:

`dependency`, `external-api`, `schema-change`, `module`, `interface`, `config`, `handoff` (a new agent/subagent/pipeline stage), and `rework` (a fix, re-review or retest spawned by a failure, these count, because failure breeds failure and the loop is only visible if counted).

Run `python scripts/lusser.py parts` to draft candidate rows (manifest changes, migrations, new source files, new exports) from the diff against the base: `--base <ref>`, else `repo.default_branch` in `config_project.json`, else `main`. Treat the draft as a floor: you may add rows to it, never remove mechanical ones without saying why.

If the count reaches the budget: stop, show the ledger, and ask whether to raise the budget, cut scope, or replace bespoke parts with proven ones. Never quietly continue.

### 4. Check: cover every clause with something that isn't you

Map each clause to checks in `checks.toml`. Kinds, from weakest to strongest:

| Kind | What it is | Fails differently from the agent? |
|---|---|---|
| `model-review` | An agent reading the code | No |
| `model-test` | A test written after seeing the implementation | No |
| `spec-test` | A test written from the clause text alone, before or without seeing the implementation | Partly |
| `property` | Property-based / fuzz testing over generated inputs | Yes, finds inputs nobody thought of |
| `differential` | Same inputs through a reference implementation or the old system; outputs compared | Yes |
| `real-input` | Recorded production data, real fixtures, or a real call to the external system | Yes |
| `human-accept` | The person it was built for tried it and signed off | Yes |

Rules the checker enforces (`python scripts/lusser.py check`):

- Every clause needs at least one check that is **not** `model-review` or `model-test`.
- Every `[critical]` clause needs at least one of `real-input`, `differential`, `human-accept`.
- Every ambiguity must have a resolution.
- `spec-test`, `property`, `real-input` and `differential` refs that look like paths must exist.
- Parts count must be within budget.

Practical guidance on writing each kind, per language, is in `references/check-kinds.md`. Read it when you reach this step.

For `spec-test`: write the tests **first**, from the clause, and commit them before the implementation. In Claude Code, better still, have a subagent write them given only `spec.md`. They are still written by a model, so they are not enough on their own, that is why the rule requires a stronger kind alongside.

Checking time is progress. Report coverage of clauses, not files written.

### 5. Close

Run `python scripts/lusser.py check`. It prints the ledger summary (n parts, p^n at the assumed p), coverage per clause, and fails on any rule above. Do not call the work done while it fails. Do not satisfy it by retagging a `model-test` as `spec-test` or by inventing a `human-accept` line; the checker cannot tell, and the only person it fools is the one who ships.

### 6. After shipping: the only benchmark that matters

When a defect is found in production, append to `escapes.md`: the clause it broke (or "no clause", itself a finding), the parts involved, and which check kinds covered that clause and missed. Over time this shows your own reliability per part and which check kinds earn their keep on your stack. Public benchmarks cannot tell you this.

## Things this skill deliberately does not do

- It adds no runtime parts to the shipped software. The checker is a single stdlib script that reads three text files.
- It does not add reviewer agents or approval gates on top of the work. Those are more parts of the same kind.
- It does not treat rollback-and-retry as a check. A retry catches the mistakes that announce themselves; the ones that look right survive it.
- It does not compute a real probability. `p^n` is a budget-keeping figure at an assumed `p`; "parts" are a judgement call. Its job is to make additions feel expensive, because they are.

## When the user pushes back

Common objections and honest answers:

- *"Parts aren't independent, so p^n overstates it."* True, and interaction between parts grows faster than the count, which understates it. The field data (DORA, the Cursor MSR study) shows the direction the arithmetic predicts.
- *"Just add another model to review it."* Models from different vendors share most of their mistakes, and the better they are, the more they share. A second reader is not a second kind of check.
- *"We're in a hurry."* A squeeze helps only if the rush costs each remaining part almost nothing. It rarely does. Cut scope deliberately and keep the checking.
