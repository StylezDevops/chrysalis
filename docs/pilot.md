# Piloting the method on a team

The evidence behind Chrysalis comes from five projects, most of them built by one developer, and the
real-repository validation shows only that setting a project up is safe. It does not show that the
method pays for itself on someone else's team. A pilot is how a team finds out, with numbers rather
than impressions. This page says how to run one.

## Shape

- One team, one repository, 4 to 6 weeks. Long enough for defects to escape and be traced.
- Run `chrysalis.py apply` on a branch, read the proposals, and merge what the team accepts.
- Start from the defaults in `PROPORTION.md`. Change a rule only through `adapt` (below), never by
  quietly skipping it.
- Name one person who reviews the log each week and owns the decisions it leads to.

## What to record

Per change, one row in `docs/pilot-log.md` (copy `templates/pilot-log.md`):

| Field | Where it comes from |
|---|---|
| change | the PR or commit |
| class | `chrysalis.py classify --base <branch>` |
| declared class | what the author thought it was before running classify |
| method minutes | time spent on what the class asked for: spec, tests shown red, audit, register row, handover |
| build minutes | time spent on the change itself |
| caught | defects the method's checks caught before merge, with the check that caught each |
| escaped | defects found after merge, filled in later, with the class of the change that let each through |

Per week, from the tools:

| Measure | Command |
|---|---|
| doctor result | `chrysalis.py doctor --repo .` |
| open, scheduled and accepted faults | `chrysalis.py register check` (the summary line) |
| controls that went red as required | `chrysalis.py gates run --controls` |

## What the numbers answer

| Question | Read it from |
|---|---|
| Does the overhead scale down? | method minutes as a share of build minutes, by class. C0 should be close to zero. |
| Are the classes right? | changes where the declared class was lower than classify's, and escapes by class. Escapes from C0 changes mean the C0 boundary is too generous for this codebase: tighten `change.small_lines` or add `change.critical_paths`. |
| Do the checks catch what they claim? | caught against escaped, per check. A check that never catches anything and costs time is a candidate to adapt; a control that never goes red is broken (U2). |
| Which rules are habits rather than safeguards? | practices the team adapted, and whether escapes rose afterwards. |

## Adapting a rule

A scaled rule or a practice can be adapted when the log supports it. Add an entry to `adapt` in
`config_project.json`:

```json
"adapt": [
  {"rule": "U12", "change": "a handover only when work is left open at the end of a session",
   "reason": "pilot weeks 1 to 3: 41 of 44 sessions ended with nothing open",
   "decided": "A. Lead (human, 2027-01-15)", "revisit": "2027-04-15"}
]
```

`validate` refuses an adaptation of a control, an entry without a human decision and an unknown field.
`AGENTS.md` shows the adaptation beside the rule, and `doctor` fails once the revisit date passes, so
an adaptation is a decision with an expiry, not a permanent exemption.

## Ending the pilot

Write an ADR (`templates/adr.md`): what was measured, what was adapted and why, the escapes and their
classes, and whether to keep the method. Send the numbers upstream as an issue on the Chrysalis
repository if you are willing to; evidence from other teams is what this method lacks most.
