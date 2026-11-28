# Proportion

How much each universal rule in `METHOD.md` asks of a change. This file is the one source of each
rule's grade; `chrysalis.py` reads the table below and never restates it.

A one-line fix should not cost what a migration costs, and some rules matter more than others. Each
universal rule has a grade:

| Grade | What it means | Can a project adapt it? |
|---|---|---|
| control | Applies in full to every change it can reach. Without it a green result cannot be trusted. | No |
| scaled | Its weight follows the change class below. | Yes, with a recorded human decision |
| practice | The working habit the evidence came from. A team may find another that keeps the controls. | Yes, with a recorded human decision |

Every change has a class:

| Class | A change is in it when |
|---|---|
| C0 | It touches docs only, or it changes at most `change.small_lines` lines (default 20), adds no file, and touches no dependency manifest, migration, gate, hook, CI file or path in `change.critical_paths`. Where `risk.live_production` holds, only a docs-only change is C0. |
| C1 | It is neither C0 nor C2. |
| C2 | It touches a path in `change.critical_paths`, a migration, a dependency manifest, or the checking machinery (gates, hooks, CI). |

`chrysalis.py classify` reads the diff, prints the lowest class the change may take with its reasons,
and lists what that class asks for from the table below. Anyone may raise a change's class. Nobody
may lower it below what the diff shows: `classify --declared C0` fails when the diff needs C1.

| Rule | Grade | C0 asks for | C1 asks for | C2 asks for | Enforced by |
|---|---|---|---|---|---|
| U1 | control | in full | in full | in full | `register check` needs the before and after numbers; measuring relies on people |
| U2 | control | in full | in full | in full | `gates validate` needs a control per gate; `gates run --controls` fails a control that stays green |
| U3 | scaled | for a defect, a register row and a regression test | also the shape hunt and the recorded gate, rule or ADR decision | also a bug-class entry when the shape can recur | `register check` |
| U4 | scaled | none beyond the tests that already cover the line | a test of the change, seen red first | also a sweep or property test, and the whole-pipeline test | people and the audit |
| U5 | scaled | none beyond reading the diff (U13) | 1 fresh-context audit round | 2 audit rounds | people; `templates/audit-record.md` |
| U6 | control | in full | in full | in full | the deferral hook (Claude Code, git, pre-commit, adapter); `register check`; `doctor` |
| U7 | practice | none | a hook when a mistake repeats | a hook when a mistake repeats | the hook tests in `hooks/` |
| U8 | control | in full | in full | in full | the project's own parity checks; people |
| U9 | control | in full | in full | in full | the project's docs-currency gate, if it has one; people |
| U10 | scaled | the commit states the claim and the check that shows it | a minimal lusser spec | a full lusser spec | `lusser check`; `classify` says which applies |
| U11 | scaled | none | an ADR when the change makes a lasting decision | an ADR for a lasting decision, with the cheaper option priced | people |
| U12 | practice | none | the handover rewritten at the end of the session | the handover rewritten at the end of the session | `doctor` checks the handover exists |
| U13 | control | in full | in full | in full | the `block_piped_register` hook; people |
| U14 | control | in full | in full | in full | people |
| U15 | scaled | the build, the unit tests and the fast static checks | also the gates the change touches | also the full gate set | `classify` lists them; people run them |
| U16 | practice | one builder | one builder unless the package earns delegation | one builder unless the package earns delegation | the `worktree` commands; `agents.max_parallel_agents` |
| U17 | control | in full | in full | in full | people; `validate` for this tool's own config |
| U18 | control | in full | in full | in full | people |
| U19 | control | in full | in full | in full | people; `validate` for this tool's own config |
| U20 | control | in full | in full | in full | people; `templates/verification.md` |
| U21 | control | in full | in full | in full | people; the audit brief asks about siblings |

"Relies on people" is stated, not hidden: the tools check structure and evidence, and they cannot
tell whether an audit was independent or a measurement went through the shipping path.

A project adapts a scaled rule or a practice under `adapt` in `config_project.json`, one entry per
rule: what changes, why, who decided it with the date (`(human, YYYY-MM-DD)`) and a revisit date.
`validate` refuses an adaptation of a control, an entry with no human decision, and an unknown field.
`doctor` fails once the revisit date has passed. The rules list in `AGENTS.md` shows each adaptation.
