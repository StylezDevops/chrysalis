"""classify: the class of a change from its diff, and what that class asks for (C15)."""

from __future__ import annotations

import pathlib

import proportion

from common import git_run, resolve_base, sabotaged
from project_config import print_questions, repo_config
from rules import grades
from scaffold import adapted_note


def diff_changes(repo: pathlib.Path, base: str) -> list[dict] | None:
    """Every path that differs from base, committed or not, plus untracked files, as
    {path, status, lines}; lines is None for a binary file. None when git cannot diff."""
    c1, numstat = git_run(repo, "diff", "--numstat", "--no-renames", base)
    c2, names = git_run(repo, "diff", "--name-status", "--no-renames", base)
    c3, others = git_run(repo, "ls-files", "--others", "--exclude-standard")
    if c1 or c2 or c3:
        return None
    lines = {}
    for row in numstat.splitlines():
        bits = row.split("\t")
        if len(bits) == 3:
            lines[bits[2]] = None if bits[0] == "-" else int(bits[0]) + int(bits[1])
    out = []
    for row in names.splitlines():
        bits = row.split("\t")
        if len(bits) == 2:
            out.append({"path": bits[1], "status": bits[0][0], "lines": lines.get(bits[1], 0)})
    for path in others.splitlines():
        try:
            data = (repo / path).read_bytes()
        except OSError:
            continue
        out.append({"path": path, "status": "A", "lines": None if b"\0" in data[:8000] else data.count(b"\n")})
    return out


def cmd_classify(args) -> int:
    repo = pathlib.Path(args.repo).resolve()
    cfg, qs = repo_config(repo, args.config)
    if qs:
        print("FAIL the config must validate before a change can be classified:")
        print_questions(qs)
        return 2
    base, source = resolve_base(repo, args.base)
    if base is None:
        print(f"FAIL {source}")
        return 1
    code, _ = git_run(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if code:
        print(f"FAIL base {base!r} ({source}) does not exist in {repo}")
        return 1
    changes = diff_changes(repo, base)
    if changes is None:
        print(f"FAIL git could not diff {repo} against {base}")
        return 1
    cls, reasons = proportion.classify(changes, cfg)
    if sabotaged("classify-always-c0"):
        cls = "C0"
    print(f"base branch: {base} ({source})")
    print(f"class: {cls}")
    for level, why in reasons:
        print(f"  {level}  {why}")
    produce, controls = proportion.obligations(grades(), cls)
    print(f"{cls} asks for:")
    for rid, what in produce:
        print(f"  {rid}  {what}" + (adapted_note(cfg, rid) if cfg else ""))
    print(f"controls in force for every class: {', '.join(controls)}")
    if args.declared:
        if proportion.CLASSES.index(args.declared) < proportion.CLASSES.index(cls):
            print(f"FAIL declared {args.declared}, but the diff needs {cls}: a class is never lowered")
            return 1
        print(f"declared {args.declared}: OK")
    return 0
