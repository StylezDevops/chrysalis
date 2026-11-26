---
name: chrysalis-init
description: Set up a new or existing project on the Chrysalis method. Validates config_project.json, asks the user about every gap, inspects the repository, lays the framework files over it without changing anything already there, and turns the generated initial.md and backlog into a real starting point. Use when the user says "initialise this project", "set up chrysalis", "start a new project with the framework", "apply the method to this repo", or points at a config_project.json.
---

# chrysalis-init

The tool does the mechanical part; this skill does the part that needs judgement and the user. Rule
IDs (U1, K4 and so on) refer to `METHOD.md` in the Chrysalis repo. Read the ones that come up rather
than working from memory.

`CHRYSALIS` below means the Chrysalis repo path. `REPO` is the project being set up.

## 1. Config

1. If `REPO/config_project.json` does not exist, copy `CHRYSALIS/config/config_project.example.json`
   there and fill what you can from the conversation and from the repo itself. Field meanings are in
   `CHRYSALIS/config/README.md`.
2. Run `python CHRYSALIS/scripts/chrysalis.py validate --config REPO/config_project.json`.
3. Every `Q` line it prints is a question for the user. Ask them together, in one message, with your
   recommended answer beside each. Do not fill a risk flag by guessing: each one switches rules on or off.
4. Repeat until validate prints `config: OK`.

## 2. Inspect before writing

1. Run `chrysalis.py inspect REPO` and read the inventory.
2. Run `chrysalis.py plan REPO --config REPO/config_project.json`. Nothing is written.
3. Show the user the plan: what will be created, what is reused (and from where), and what will only
   be proposed because a file is already there. For an existing repo, say plainly that no existing file
   will change.

## 3. Apply

Run `chrysalis.py apply REPO --config REPO/config_project.json`. It creates absent files with exclusive
create, writes proposals under `REPO/.chrysalis/run-<time>/proposals/`, records the inventory and the
rules in force, and runs no git command that writes. Read its output; do not summarise it from memory.

## 4. Make initial.md real

`initial.md` arrives with the config filled in and the judgement sections marked TO DO. Fill them in
with the user:

- **Architecture**: components, boundaries, what persists, what talks to the outside world. Each lasting
  choice becomes an ADR from the template (U11).
- **Constraints**: each with its source.
- **Risks and how they are checked**: every risk names the gate in `gates.toml`, or the human check,
  that would catch it. A risk with no check is an open question.
- **Approach**: the first milestone, what "working" means for it, and the first 3 to 5 backlog items.

For an existing repo, read the existing contract files (CLAUDE.md, AGENTS.md, specs, ADRs, register)
first and write initial.md from what is already decided. Do not reopen settled decisions.

## 5. Backlog, spec and gates

1. Write the first epic and its stories in `docs/backlog.md`, each with observable acceptance criteria.
2. Write the first milestone's `.lusser/spec.md`: clauses, ambiguities as questions, a part budget. Ask
   the ambiguities and stop until they are answered (U10).
3. Add the project's own gates to `gates.toml`, each with a control that makes it fail. Run
   `chrysalis.py gates run --controls` and show that every control goes red before calling a gate real
   (U2).

## 6. Proposals for existing files

For each file under `.chrysalis/run-*/proposals/`, show the user the difference from the existing file
and let them decide what to merge. Never merge a proposal yourself unless the user says to.

## 7. Hand over

Write `docs/handover.md` (or the project's existing equivalent): what was set up, which questions are
still open, and the first backlog item to start with.

## What this skill does not do

- It never commits, pushes, deletes or rewrites anything in REPO.
- It does not install hooks into `.claude/settings.json`. If the user wants the hooks from
  `CHRYSALIS/hooks/`, show them the settings snippet in `CHRYSALIS/hooks/README.md` and let them add it.
- It does not read or copy files that look like secrets or keys; `inspect` skips them by name.
