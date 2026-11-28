#!/usr/bin/env python3
"""chrysalis: set up a project on the method in METHOD.md without damaging what is already there.

Subcommands:
  validate --config FILE          check config_project.json; open questions exit 2
  rules --config FILE             list the rules in force for that config
  rules --list-conditions         list each conditional rule and its parsed condition
  inspect REPO                    print a JSON inventory of what the repo already has
  plan REPO [--config FILE]       show what apply would do, change nothing
  apply REPO [--config FILE]      create absent files, write proposals for present ones
  gates validate [--file F]       check gates.toml has purpose, pass rule and control per gate
  gates run [--file F] [--controls]  run automated gates, or their controls (which must fail)
  register check [--file F] [--release]  check each row's state carries its evidence (U3, U6)
  classify [--repo R] [--base B] [--declared C]  the change's class (C0 to C2) and what it asks for
  doctor [--repo R] [--release]   read-only compliance check of a project on the method
  skills install [--dest D] [--prefix P] [--apply]  copy the skills, never over a different one
  check                           framework self-check: evidence, conditions, no copied text
  worktree new NAME [--repo R]    worktree on branch agent/NAME from the current base (U16)
  worktree finish NAME [--build-dir D]  remove it, its branch and build dir, only if merged and clean
  worktree sweep [--apply]        list (or remove) every merged agent branch and its worktree

Standard library only. Python 3.11+ (tomllib).

This file is the command line only. Each command lives in a module of its own beside it:
  common          paths, git, the sabotage switch, the Markdown row splitter, the base-branch rule
  project_config  config_project.json schema and validation       rules        METHOD.md and the K table
  proportion      grades, change classes, adaptations              inventory    inspect
  scaffold        plan and apply                                   gates        gates validate and run
  register        register check                                   selfcheck    check
  worktree        worktree new, finish and sweep                   change_class classify
  doctor          doctor                                           skills_install  skills install

apply never edits, deletes or renames a file that existed before it ran, and never runs a git command
that writes. New files are opened with exclusive create, so a file that appears between the plan and
the write is left alone rather than overwritten.

`gates run` passes each command to the shell, because gate commands are written by the project
owner in the project's own gates.toml, the same trust level as a Makefile. Never point it at a
gates.toml you did not write or review.

CHRYSALIS_SABOTAGE=<name> arms a deliberate defect so tests/run_all.py --sweep can prove the tests
see it. Unset, it does nothing.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import proportion

from change_class import cmd_classify
from common import METHOD
from doctor import cmd_doctor
from gates import cmd_gates
from inventory import DEFAULT_DEPTH, inspect
from project_config import load_config, print_questions, questions
from register import cmd_register
from rules import Condition, parse_method, select_rules
from scaffold import cmd_apply
from selfcheck import cmd_check
from skills_install import cmd_skills
from worktree import cmd_worktree


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="chrysalis", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--config", default="config_project.json")

    p = sub.add_parser("rules")
    p.add_argument("--config")
    p.add_argument("--list-conditions", action="store_true")

    depth_help = f"folder levels searched for existing assets (default {DEFAULT_DEPTH})"
    p = sub.add_parser("inspect")
    p.add_argument("repo")
    p.add_argument("--max-depth", type=int, default=DEFAULT_DEPTH, help=depth_help)

    for name in ("plan", "apply"):
        p = sub.add_parser(name)
        p.add_argument("repo")
        p.add_argument("--config")
        p.add_argument("--max-depth", type=int, default=DEFAULT_DEPTH, help=depth_help)
        p.add_argument("--home", help="home folder for installing the guardrails file (default: yours)")
        p.add_argument("--no-home", action="store_true",
                       help="write nothing outside the repo: skip installing the guardrails file")

    p = sub.add_parser("gates")
    p.add_argument("action", choices=["validate", "run"])
    p.add_argument("--file", default="gates.toml")
    p.add_argument("--controls", action="store_true")
    p.add_argument("--only", nargs="*")

    p = sub.add_parser("register")
    p.add_argument("action", choices=["check"])
    p.add_argument("--file", default="docs/register.md")
    p.add_argument("--root")
    p.add_argument("--release", action="store_true", help="also fail on any OPEN row (U6)")

    p = sub.add_parser("check")
    p.add_argument("--method")
    p.add_argument("--proportion")
    p.add_argument("--templates")
    p.add_argument("--sources", help="folder of .py files to hold to the line limit (default: this repo)")

    p = sub.add_parser("worktree")
    p.add_argument("action", choices=["new", "finish", "sweep"])
    p.add_argument("name", nargs="?")
    p.add_argument("--build-dir", help="finish: the agent's build directory outside the worktree, removed too")
    p.add_argument("--apply", action="store_true", help="sweep: remove what it lists (default: dry run)")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", help="base branch (default: repo.default_branch in the repo's "
                                  "config_project.json, else main)")
    p.add_argument("--root", help="folder that holds the worktrees (default: <repo>-worktrees beside it)")

    p = sub.add_parser("classify")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", help="base to diff against (default: repo.default_branch in the repo's "
                                  "config_project.json, else main)")
    p.add_argument("--config", help="default: config_project.json in the repo, if present")
    p.add_argument("--declared", choices=proportion.CLASSES, help="fail if the diff needs a higher class")

    p = sub.add_parser("doctor")
    p.add_argument("--repo", default=".")
    p.add_argument("--config", help="default: config_project.json in the repo")
    p.add_argument("--release", action="store_true", help="also fail on any OPEN register row")

    p = sub.add_parser("skills")
    p.add_argument("action", choices=["install"])
    p.add_argument("--dest", help="skills folder (default: ~/.claude/skills)")
    p.add_argument("--prefix", default="", help="install each skill as PREFIX+name, beside any of that name")
    p.add_argument("--apply", action="store_true", help="write (default: dry run)")

    args = ap.parse_args(argv)
    if args.cmd == "worktree":
        return cmd_worktree(args)
    if args.cmd == "classify":
        return cmd_classify(args)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "skills":
        return cmd_skills(args)

    if args.cmd == "validate":
        qs = questions(load_config(pathlib.Path(args.config)))
        if qs:
            print_questions(qs)
            return 2
        print("config: OK")
        return 0
    if args.cmd == "rules":
        if args.list_conditions:
            for rid, cond in parse_method(METHOD.read_text(encoding="utf-8"))[1]:
                Condition(cond)
                print(f"{rid}  {cond}")
            return 0
        if not args.config:
            ap.error("rules needs --config or --list-conditions")
        cfg = load_config(pathlib.Path(args.config))
        qs = questions(cfg)
        if qs:
            print_questions(qs)
            return 2
        for rid, title in select_rules(cfg):
            print(f"{rid}  {title}")
        return 0
    if args.cmd == "inspect":
        print(json.dumps(inspect(pathlib.Path(args.repo).resolve(), args.max_depth), indent=2))
        return 0
    if args.cmd in ("plan", "apply"):
        return cmd_apply(args, write=args.cmd == "apply")
    if args.cmd == "gates":
        return cmd_gates(args)
    if args.cmd == "register":
        return cmd_register(args)
    if args.cmd == "check":
        return cmd_check(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
