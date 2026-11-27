# Chrysalis

An engineering method for building software with AI coding agents, written down from what already
worked across real projects, plus the tools that apply it to a new or existing repository without
touching what is already there.

The idea behind it: an agent does not get to mark its own homework. Every rule here puts a different
kind of check between the model and the merge: a number measured before and after, a test that has
been seen to fail, a hook that refuses a known mistake, a human answer to an ambiguous spec.

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
K10 for software that changes data it does not own. `docs/discovery.md` shows which project each rule
came from.

`lusser` is named after Lusser's product law: a system works only if every part works, so its odds are
the product of each part's odds. The lusser skill keeps the part count down, gets a human to resolve
ambiguity in the spec before building, and ties every spec clause to a check.

## What is in the repo

| Path | What it is |
|---|---|
| `METHOD.md` | The rules. 20 universal (U1 to U20) and 10 conditional (K1 to K10), each with its evidence. |
| `docs/discovery.md` | How the rules were found: which projects, which files, what was inferred. |
| `config/` | `config_project.json` fields and a filled example. |
| `scripts/chrysalis.py` | The tool: validate, rules, inspect, plan, apply, gates, register check, worktree (new, finish, sweep), check. Standard library only. |
| `templates/` | What `apply` writes: CLAUDE.md, initial.md, backlog, register, handover, ADR, Definition of Ready and Done, bug classes, names that do not exist, verification, fix, audit and change records, gates.toml and lusser files; plus a change request and runbook for live systems and a threat model where money, personal data or auth are involved. |
| `skills/` | Claude Code skills: `chrysalis-init` plus 6 more (table below). |
| `hooks/` | 4 Claude Code PreToolUse hooks, each with tests. |
| `guardrails/` | The general code-writing guardrails `apply` installs to `~/.claude/` if absent. |
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

On an existing repository, `apply`:

- creates only files that are absent, using exclusive create;
- reuses what the repo already has (an ADR folder, a defect register, a gate script, a `.lusser/`)
  instead of adding a second one;
- writes a proposal under `.chrysalis/run-<time>/proposals/` for any file that already exists;
- runs no git command that writes.

The `chrysalis-init` skill walks an agent through the rest with the user: the questions, `initial.md`,
the first backlog items, the first lusser spec and the project's own gates.

## Tooling, and why it is not the point

My own setup makes some tools mandatory wherever they are available. Every shell command goes through
[rtk](https://github.com/rtk-ai/rtk), which strips noise from command output so an agent spends its
context on what matters. Code is read and edited through [Serena](https://github.com/oraios/serena),
which works on symbols through a language server instead of reading whole files. The agent is Claude
Code, and the hooks in `hooks/` are Claude Code PreToolUse hooks.

That is simply what I use at the moment. Chrysalis does not depend on any of it: `chrysalis.py` and
`lusser.py` need only Python and git, and the rules never name a tool. Swap in whatever you prefer: a
different agent, editor, output filter or code index. The in-work project shows it carries over: the
method started there, in VS Code with AI extensions, before any of these tools were in use.

What matters is the thinking behind the method. The agent does not mark its own homework. A check
counts once it has been seen to fail. A defect becomes structure. A missing input stops the work. A
claim needs evidence. Any tool that helps you hold to those is a good fit; one that gets in the way is
not.

## Using it in a team

### The method lives in the repository

Everything `apply` writes is a file in the repo, so a team shares it through git, not through one
person's setup. Every developer, and every agent session they start, reads the same CLAUDE.md, gates,
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

1. Pilot on 1 repository with 1 team. Run `plan`, read what it would do, then `apply`. Answer the
   questions together.
2. Put `chrysalis.py gates run` into CI, so a gate blocks a merge for everyone, not only for the person
   who wrote it.
3. Put the hooks into the project's `.claude/settings.json`, so every developer's agent refuses the same
   known mistakes.
4. Use the register as the team's shared defect list. A defect closes only with a measured number and a
   regression test that was red before the fix.
5. After a few weeks, read the register back. A class of defect that keeps coming up becomes a new gate
   or rule. The team's rules then grow from the team's own defects, the same way these grew from mine.

### As a workshop

The method can be taught in 1 session on a team's own repository: run `apply` live, resolve the
ambiguities in a first spec, write 1 gate and watch its control go red. People leave with the files in
their repo and 1 gate they have seen fail.

### What a team rollout would need to test

- Who resolves an ambiguity when several people can.
- How long the gates take in CI on a large repository.
- Whether the hooks suit every developer's setup.

## Installing the skills and hooks

PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude\skills | Out-Null
Copy-Item -Recurse $HOME\chrysalis\skills\* $HOME\.claude\skills\
```

bash:

```bash
mkdir -p ~/.claude/skills
cp -R ~/chrysalis/skills/* ~/.claude/skills/
```

The copy overwrites any skill with the same name in `~/.claude/skills`. Hooks are wired by hand; the
settings snippet is in `hooks/README.md`.

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

Measured on 2026-11-27, Windows 11, Python 3.14. Each line can be re-run with its command.

| Check | Command | Result |
|---|---|---|
| Spec tests for every clause | `python tests/run_all.py --only chrysalis` | 51 tests, all pass |
| lusser tests | `python tests/run_all.py --only lusser` | 15 tests, all pass |
| Hook tests | `python tests/run_all.py --only hooks` | 24 block and 24 allow cases, 0 wrong |
| Evidence: cited files exist and hold their quotes | `python tests/run_all.py --only evidence` | 3 tests, all pass |
| Each of 15 deliberate defects is caught by a test naming its clause | `python tests/run_all.py --sweep` | 15 of 15 caught |
| `apply` on copies of 4 real repositories and 1 new project | `python tests/validate_real.py` | 0 files changed or deleted across 5,709; all 5 pass; see `docs/validation.md` |
| 7 automated gates | `python scripts/chrysalis.py gates run` | 7 pass |
| Every gate's control goes red | `python scripts/chrysalis.py gates run --controls` | 7 of 7 red |
| Spec coverage and part budget | `python skills/lusser/scripts/lusser.py check` | OK; 14 clauses covered, 16 of 16 parts |

5 defects have been found in Chrysalis itself and fixed with regression tests: 3 by the
real-repository run, and 2 where a byte-order mark written by PowerShell broke file reading. They are
in `docs/register.md` with their numbers.

The real-repository validation and the evidence test read local copies of the source projects. Their
paths are in a gitignored file, `tests/evidence_roots.local.json`. On another machine the 2 checks skip,
and they report a skip, not a pass. The last full run is in `docs/validation.md`: 4 real repositories
and 1 new project, 5,709 files, 0 changed or deleted.

## Licence

MIT. See `LICENSE`.

## Limits

- `apply` gives a project its files and structure. Whether the project then follows the method is down
  to the people and agents working in it, and the gates they write.
- The validation copies tracked files only, so assets that exist only as ignored files were not tested.
- The rules come from 1 work project and 3 of my own over about a year. They are evidence of what
  worked there, not proof that they generalise.
