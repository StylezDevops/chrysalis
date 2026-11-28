# Chrysalis

[![CI](https://github.com/StylezDevops/chrysalis/actions/workflows/ci.yml/badge.svg)](https://github.com/StylezDevops/chrysalis/actions/workflows/ci.yml)

An engineering method for building software with AI coding agents, written down from what already
worked across real projects, plus the tools that apply it to a new or existing repository without
touching what is already there.

The idea behind it: an agent does not get to mark its own homework. Every rule here puts a different
kind of check between the model and the merge: a number measured before and after, a test that has
been seen to fail, a hook that refuses a known mistake, a human answer to an ambiguous spec.

## How much it asks

The rigour is scaled to the change, and small changes are cheap on purpose. `PROPORTION.md` grades
every rule:

| Grade | Rules | What it means |
|---|---|---|
| control | 12 | Applies to every change and cannot be switched off: a check must be able to fail, a report is a claim, fail closed, every fault on the record and the rest. |
| scaled | 6 | Weighted by the change class: specs, tests, audits, ADRs and the gates run. |
| practice | 3 | Working habits (hooks for repeated mistakes, handovers, one builder at a time). A team may adapt them, with a recorded human decision and a revisit date. |

`chrysalis.py classify` reads a diff and gives it a class, with reasons. It refuses a declared class
lower than the diff needs:

| Class | Typical change | What it asks for beyond the controls |
|---|---|---|
| C0 | a docs edit, a one-line config fix | 4 items: the claim and its check in the commit message, the build and unit tests, a register row and test only if it fixes a defect, one builder |
| C1 | a feature, a new file | 9 items, among them a minimal spec, a test seen red, 1 audit round and the touched gates |
| C2 | a critical path, a migration, a dependency, the gates themselves | the same 9, heavier: a full spec, 2 audit rounds, the full gate set |

A fault is never hidden, but it need not block everything. A register row is OPEN (blocks a release),
CLOSED (fixed, with numbers and a regression test), SCHEDULED (an owner and a due date) or ACCEPTED (a
named person carries the risk until a revisit date). A deferral marker in code cites its row, as in
`(R-12)`.

`PROPORTION.md` also says, rule by rule, what enforces it: a hook, a gate, `doctor`, or people. Where
the answer is people, it says so.

## Where it came from

The method began at work. The first version was written on a project I build in my job, called "the
in-work project" throughout this repo: a data-integration platform built since late 2025, in VS Code
with AI extensions rather than a dedicated agent tool. It belongs to my employer, so it is not named
here and none of its code or documents are in this repository. A large share of the original rules
started there: fail fast on a missing prerequisite, zero warnings, no "for now" code, one
transformation for every path, every record either written or quarantined, a decision register in each
ADR.

I then carried the method into my own projects through 2026, and each one made it stricter. Measured
on 2026-11-26 from each project's git history and defect register:

| Project | What it is | Commits | Period | Defects |
|---|---|---|---|---|
| MIDAS | Wavetable bass synthesiser, VST3 and AU | 508 | July to September 2026 | 79 bug classes, each with the gate that now catches it |
| CHRYSOS | Sampler instrument, VST3 and AU | 1,031 | September to November 2026 | 112 rows in the register's Closed table, each with a measured number |
| Substrate | Music provenance platform | 1,064 | June to November 2026 | 275 of 311 audit rows done, none marked done without numbers |

MIDAS made "measure first" a hard rule. CHRYSOS added hooks born from incidents, the defect register,
ADRs and the sabotage gate that proves every gate can fail. Substrate added the docs-currency gate and
blast-radius classes for live systems.

Chrysalis, published in November 2026, packages all of it. On 2026-11-27 every document and internal
note in the in-work project was read to its last line. Its practices the later projects had dropped
came back, and its defects became rules where none existed: fail closed (U17), one outcome per unit of
work (U18), config checked when it loads (U19), a mechanism counts once it is shown to run (U20), and
K10 for software that changes data it does not own. The owner added U21 the same day: a behaviour promised
across a family of interchangeable things holds for every member. `docs/discovery.md` shows which
project each rule came from.

`lusser` is named after Lusser's product law: a system works only if every part works, so its odds are
the product of each part's odds. The lusser skill keeps the part count down, gets a human to resolve
ambiguity in the spec before building, and ties every spec clause to a check.

## What is in the repo

| Path | What it is |
|---|---|
| `METHOD.md` | The rules. 21 universal (U1 to U21) and 10 conditional (K1 to K10), each with its evidence. |
| `PROPORTION.md` | Each rule's grade, the change classes, what each class asks for, what enforces each rule, and how a project adapts one. |
| `docs/discovery.md` | How the rules were found: which projects, which files, what was inferred. |
| `docs/pilot.md` | How a team pilots the method and measures its overhead before adopting it. |
| `config/` | `config_project.json` fields and a filled example. |
| `scripts/` | The tool, `chrysalis.py`: validate, rules, inspect, plan, apply, classify, doctor, gates, register check, worktree (new, finish, sweep), skills install, check. One module per command, none over 500 lines. Standard library only. |
| `templates/` | What `apply` writes: AGENTS.md (with a CLAUDE.md that imports it), a CI workflow, initial.md, backlog, register, handover, ADR, Definition of Ready and Done, bug classes, names that do not exist, verification, fix, audit and change records, a pilot log, gates.toml and lusser files; plus a change request and runbook for live systems and a threat model where money, personal data or auth are involved. |
| `skills/` | Agent skills: `chrysalis-init` plus 6 more (table below). |
| `hooks/` | 5 hooks that refuse known mistakes (an unverified package install among them), an adapter (`check.py`) that runs them from any tool, and a git pre-commit form of the deferral-marker hook, each with tests. |
| `.pre-commit-hooks.yaml` | The deferral-marker hook for the pre-commit framework. |
| `.github/workflows/ci.yml` | Every gate that needs no local data, with its control, on Linux and Windows; the quick start below on an empty project; the pre-commit hook run for real. |
| `AGENTS.md`, `config_project.json`, `docs/handover.md` | This repo on its own method: `doctor` checks it (gate D1). |
| `guardrails/` | The general code-writing guardrails `apply` installs to `~/.claude/` if absent (`--no-home` skips it). |
| `tests/` | Spec tests per clause, lusser tests, the sabotage sweep and the real-repository validation. |
| `.lusser/` | This repo's own spec, parts ledger and checks. |
| `gates.toml` | This repo's own gates. Each automated gate has a control. |

## Using it on a project

Requires Python 3.11 or later and git. Nothing to install.

PowerShell:

```powershell
git clone https://github.com/StylezDevops/chrysalis.git $HOME\chrysalis
Copy-Item $HOME\chrysalis\config\config_project.example.json C:\path\to\project\config_project.json
# edit the config, then:
python $HOME\chrysalis\scripts\chrysalis.py validate --config C:\path\to\project\config_project.json
python $HOME\chrysalis\scripts\chrysalis.py plan  C:\path\to\project
python $HOME\chrysalis\scripts\chrysalis.py apply C:\path\to\project
```

bash:

```bash
git clone https://github.com/StylezDevops/chrysalis.git ~/chrysalis
cp ~/chrysalis/config/config_project.example.json /path/to/project/config_project.json
# edit the config, then:
python3 ~/chrysalis/scripts/chrysalis.py validate --config /path/to/project/config_project.json
python3 ~/chrysalis/scripts/chrysalis.py plan  /path/to/project
python3 ~/chrysalis/scripts/chrysalis.py apply /path/to/project
```

`validate` turns every gap or contradiction in the config into a numbered question and exits 2. `apply`
refuses to run until there are none.

After `apply`, two commands carry the method day to day:

```bash
python3 ~/chrysalis/scripts/chrysalis.py classify --repo /path/to/project   # this change's class and what it asks for
python3 ~/chrysalis/scripts/chrysalis.py doctor --repo /path/to/project     # is the project still on the method?
```

`doctor` reads, never writes. It checks the config and any adaptations, the register, every deferral
marker, the gates, the lusser spec, the rules list in AGENTS.md against the config, and the handover,
and exits 1 on any failure. On a project `apply` has just set up, only the lusser check fails: the
first spec is the human's to resolve. `apply` proposes `.github/workflows/chrysalis.yml`, which runs
both commands on every pull request, pinned to the Chrysalis commit that generated it.

On an existing repository, `apply`:

- creates only files that are absent, using exclusive create;
- reuses what the repo already has (an ADR folder, a defect register, a gate script, a `.lusser/`)
  instead of adding a second one;
- writes a proposal under `.chrysalis/run-<time>/proposals/` for any file that already exists;
- runs no git command that writes.

It searches 3 folder levels for existing assets and lists any deeper folder it skipped; in a monorepo,
pass `--max-depth` to search further. Outside the repo it writes only `~/.claude/engineering-guardrails.md`,
and only if that file is absent. `plan` names that file first, and `--no-home` skips it.

To see the result without running anything, open the latest
[CI run](https://github.com/StylezDevops/chrysalis/actions/workflows/ci.yml): the "README quick start"
job lists every file `apply` wrote into an empty project, shows the generated `initial.md`, and offers
the whole project as a download named `example-project`.

The `chrysalis-init` skill walks an agent through the rest with the user: the questions, `initial.md`,
the first backlog items, the first lusser spec and the project's own gates.

## Tooling, and why it is not the point

My own setup makes some tools mandatory wherever they are available. Every shell command goes through
[rtk](https://github.com/rtk-ai/rtk), which strips noise from command output so an agent spends its
context on what matters. Code is read and edited through [Serena](https://github.com/oraios/serena),
which works on symbols through a language server instead of reading whole files. The agent is Claude
Code.

That is simply what I use at the moment. Chrysalis does not depend on any of it: `chrysalis.py` and
`lusser.py` need only Python and git, and the rules never name a tool. `apply` writes the project's
instructions to `AGENTS.md`, which most coding agents read; the generated `CLAUDE.md` only imports it.
The hooks read Claude Code's payload, but `hooks/check.py` runs every one of them from plain arguments
(`check.py command "<cmd>"`, `check.py file PATH`, `check.py staged`) and answers with an exit code,
so any agent's hook setting, an editor task or CI can call them. The deferral-marker hook also ships as
a git pre-commit hook and for the pre-commit framework. Swap in whatever you prefer: a
different agent, editor, output filter or code index. The in-work project shows it carries over: the
method started there, in VS Code with AI extensions, before any of these tools were in use.

What matters is the thinking behind the method. The agent does not mark its own homework. A check
counts once it has been seen to fail. A defect becomes structure. A missing input stops the work. A
claim needs evidence. Any tool that helps you hold to those is a good fit; one that gets in the way is
not.

## Using it in a team

### The method lives in the repository

Everything `apply` writes is a file in the repo, so a team shares it through git, not through one
person's setup. Every developer, and every agent session they start, reads the same AGENTS.md, gates,
defect register, ADRs and spec. A new joiner gets the rules by cloning. They do not depend on who set
the project up or which machine they work on.

### Who does what

- A lead answers the questions `validate` raises and resolves ambiguities in each spec, in writing and
  with a date, before anyone builds.
- Developers and their agents take backlog items that meet the Definition of Ready, and finish them
  against the Definition of Done.
- A reviewer checks the gate results and the register row as well as the diff. The question is "what
  measured this?", not "does the code look right?".
- Work passes between people and agent sessions through the handover template, so a session that runs
  out of context or a developer who goes on leave does not take the state with them.

### Rolling it out

1. Pilot on 1 repository with 1 team, following `docs/pilot.md`. Run `plan`, read what it would do,
   then `apply`. Answer the questions together.
2. Keep the proposed `.github/workflows/chrysalis.yml` and put `chrysalis.py gates run` into CI, so
   `doctor`, `classify` and the gates block a merge for everyone, not only for the person who wrote them.
3. Wire the hooks into each developer's tool: `.claude/settings.json` for Claude Code, `hooks/check.py`
   for any other agent, the pre-commit framework or a git hook for everyone.
4. Use the register as the team's shared defect list. A defect closes only with a measured number and a
   regression test that was red before the fix. A fault the team decides to fix later is SCHEDULED; a
   risk it decides to carry is ACCEPTED by a named person. Neither is hidden, and `doctor` fails when
   its date passes.
5. Record per change its class, the minutes spent on what the class asked for, and what the checks
   caught. After a few weeks, read the log and the register back. Adapt what the numbers say is not
   paying for itself (practices and scaled rules, never controls), and turn a class of defect that keeps
   coming up into a new gate or rule.

### As a workshop

The method can be taught in 1 session on a team's own repository: run `apply` live, resolve the
ambiguities in a first spec, write 1 gate and watch its control go red. People leave with the files in
their repo and 1 gate they have seen fail.

### What a team rollout would need to test

- Whether the method's overhead pays for itself: `docs/pilot.md` lists what to record and which
  question each number answers.
- Whether the C0 boundary suits the codebase: escapes from C0 changes mean it is too generous.
- Who resolves an ambiguity when several people can.
- How long the gates take in CI on a large repository.

## Installing the skills and hooks

```bash
python3 ~/chrysalis/scripts/chrysalis.py skills install                    # dry run: what it would do
python3 ~/chrysalis/scripts/chrysalis.py skills install --apply            # into ~/.claude/skills
python3 ~/chrysalis/scripts/chrysalis.py skills install --apply --prefix chrysalis- --dest DIR
```

`skills install` never overwrites. A skill already there with the same content is skipped; one with
the same name and different content is reported as a conflict, left untouched, and the command exits
1. `--prefix` installs beside it under a new name, and `--dest` points at another tool's skills folder.
Hooks are wired by hand; `hooks/README.md` has the settings for Claude Code, other agents, git and
pre-commit.

Core skills, used by the method:

| Skill | What it does |
|---|---|
| `chrysalis-init` | Sets up a project on this method with the user, using `chrysalis.py`. |
| `lusser` | Spec clauses, a part budget and checks that fail differently from an agent; `lusser.py check` enforces them. |
| `register-loop` | Works a defect register 1 row at a time: measure, prove the detector, fix with a regression test, audit until clean. |
| `adversarial-assurance` | A review by 6 subagents that each assume the previous one is wrong, producing tests that try to falsify the code. |
| `epic-orchestrator` | Splits large work into dependency-ordered chunks for isolated subagents, each given only its own brief. |

Other skills I use. They came from the same projects but are domain-specific and not needed for the method:

| Skill | What it does |
|---|---|
| `npm-slopsquat-guard` | Verifies every npm package name against the registry before it reaches an install command. |
| `audio-plugin-audit` | Read-only review of real-time audio C++ for thread-safety, denormal, NaN and DSP faults. |

## How it was verified

Every check below except the real-repository validation also runs in CI on each push, on Ubuntu and
Windows with Python 3.11 and 3.13; the badge at the top shows the latest result. The numbers here were
measured on 2026-11-28, Windows 11, Python 3.14. Each line can be re-run with its command.

| Check | Command | Result |
|---|---|---|
| Spec tests for clauses C1 to C14 | `python tests/run_all.py --only chrysalis` | 71 tests, all pass |
| Spec tests for clauses C15 to C18 (proportion, fault states, doctor, portability) | `python tests/run_all.py --only governance` | 48 tests, all pass |
| lusser tests | `python tests/run_all.py --only lusser` | 18 tests, all pass |
| Hook tests | `python tests/run_all.py --only hooks` | 57 block and 51 allow cases, 0 wrong |
| Evidence: cited files exist and hold their quotes | `python tests/run_all.py --only evidence` | 3 tests, all pass |
| Each of 20 deliberate defects is caught by a test naming its clause | `python tests/run_all.py --sweep` | 20 of 20 caught |
| `apply` on copies of 4 real repositories and 1 new project | `python tests/validate_real.py` | 0 files changed or deleted across 5,727; all 5 pass; see `docs/validation.md` |
| 8 automated gates, including D1: this repo passes its own `doctor --release` | `python scripts/chrysalis.py gates run` | 8 pass |
| Every gate's control goes red, and its output shows the gate's own finding for the planted defect | `python scripts/chrysalis.py gates run --controls` | 8 of 8 red, each for the right reason |
| Spec coverage and part budget | `python skills/lusser/scripts/lusser.py check` | OK; 18 clauses covered, 36 of 36 parts |
| The deferral hook through the real pre-commit framework | `bash tests/precommit_real.sh` | refuses an uncited marker, allows a cited one (CI) |

18 defects have been found in Chrysalis itself and fixed with regression tests: 3 by the
real-repository run; 2 where a byte-order mark written by PowerShell broke file reading; 2 by running
the suites in a fresh clone before CI was added (a skipped test reported as a pass, and the validation
crashing instead of skipping); 3 from an outside code review (worktrees ignoring the configured
default branch, a pipe inside a table cell shifting the register's columns, and a silent folder-depth
limit); 1 found by checking that review's first fix against its siblings (U21): `lusser parts` still
ignored the configured default branch; 1 while acting on a second review: `chrysalis.py` had grown
to 1,341 lines against the method's own limit of 500, so it is now 14 modules and `check` enforces the
limit; 1 from that review's second look: `gates run --controls` took any non-zero exit as a control
going red, so every gate now declares the finding its control must show; and 5 from a source-level
review: `worktree finish` would delete a build folder inside the repository, `.git` included; a gate with
no id passed validation; a mistyped `--only` reported green; `apply` could write through a symlinked
folder to outside the repository; and the sensitive risk flags did not reach the change classifier.
They are in `docs/register.md` with their numbers.

The real-repository validation and the evidence test read local copies of the source projects. Their
paths are in a gitignored file, `tests/evidence_roots.local.json`. On another machine, CI included, the
evidence suite prints "PASS, 2 of 3 skipped" and the validation exits 3 with "SKIPPED"; neither reports
a plain pass. The last full run is in `docs/validation.md`: 4 real repositories
and 1 new project, 5,727 files, 0 changed or deleted.

## Licence

MIT. See `LICENSE`.

## Limits

- The tools enforce structure and evidence: `doctor`, `classify`, the gates, the hooks and the register
  check. They cannot tell whether an audit was really independent, a measurement really went through
  the shipping path, or a person read the diff. `PROPORTION.md` names, rule by rule, which parts rely on
  people.
- The rules come from 1 work project and 3 of my own over about a year, most of it built by one
  developer. They are evidence of what worked there, not proof that they generalise. The
  real-repository validation shows that setting a project up is safe; it does not show the method pays
  for itself on someone else's team. `docs/pilot.md` is how a team finds out.
- The validation copies tracked files only, so assets that exist only as ignored files were not tested.
- `gates run` executes the commands in the project's `gates.toml` through the shell. That file is the
  project's own executable config, like a Makefile, so Chrysalis is not a sandbox: run the gates of an
  untrusted contribution (a fork's pull request) only in a throwaway CI runner with a read-only token,
  which is how the generated workflow is set up.
- The install guard checks that a package's registry check is on record with a human's approval before
  it installs; it cannot do the check itself, which needs the network and judgement, and it does not see
  an install hidden inside a script the command runs.
