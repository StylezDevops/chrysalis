"""risk: what the change classification protects, for audit (C15). Read-only.

For each declared risk it lists the paths mapped to it and how many tracked files they cover; it lists
the infrastructure files the classifier raises to C2 on its own, any risk left without paths, and, over
the last N commits, how many were C0, C1 and C2 and why the C2 ones were.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib

import proportion

from common import git_run
from project_config import SENSITIVE_FLAGS, print_questions, repo_config


def commit_changes(repo: pathlib.Path, commit: str) -> list[dict] | None:
    """The files one commit changed, as classify reads them (path, status, lines)."""
    code, parents = git_run(repo, "rev-list", "--parents", "-n", "1", commit)
    if code:
        return None
    bits = parents.split()
    base = bits[1] if len(bits) > 1 else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # the empty tree
    c1, numstat = git_run(repo, "diff", "--numstat", "--no-renames", base, commit)
    c2, names = git_run(repo, "diff", "--name-status", "--no-renames", base, commit)
    if c1 or c2:
        return None
    lines = {}
    for row in numstat.splitlines():
        p = row.split("\t")
        if len(p) == 3:
            lines[p[2]] = None if p[0] == "-" else int(p[0]) + int(p[1])
    return [{"path": r.split("\t")[1], "status": r[0], "lines": lines.get(r.split("\t")[1], 0)}
            for r in names.splitlines() if "\t" in r]


def report(repo: pathlib.Path, cfg: dict, history: int) -> dict:
    code, tracked = git_run(repo, "ls-files")
    files = tracked.splitlines() if code == 0 else []
    critical = ((cfg.get("change") or {}).get("critical_paths")) or []
    risk = cfg.get("risk") or {}
    declared = [f for f in (*SENSITIVE_FLAGS, "infrastructure", "live_production") if risk.get(f) is True]
    paths = [{"pattern": g, "files": sum(1 for f in files if fnmatch.fnmatchcase(f, g))} for g in critical]
    infra = [f for f in files if proportion.INFRA.search(f) and not proportion.is_doc(f)]
    uncovered = [f for f in declared if f in SENSITIVE_FLAGS and not critical]
    classes = {c: 0 for c in proportion.CLASSES}
    why_c2: dict[str, int] = {}
    code, log = git_run(repo, "log", f"-{history}", "--format=%H")
    classified = 0
    for commit in (log.splitlines() if code == 0 else []):
        changes = commit_changes(repo, commit)
        if changes is None:
            continue
        classified += 1
        cls, reasons = proportion.classify(changes, cfg)
        classes[cls] += 1
        if cls == "C2":
            # Each reason counts once per commit, however many of its files share it.
            kinds = {(text.split(" is ", 1)[-1].split(" (")[0] if " is " in text else "a critical path")
                     for level, text in reasons if level == "C2"}
            for kind in kinds:
                why_c2[kind] = why_c2.get(kind, 0) + 1
    return {"declared_risks": declared, "critical_paths": paths, "stale_paths": [p["pattern"] for p in paths
            if p["files"] == 0], "infrastructure_files": len(infra), "risks_without_paths": uncovered,
            "commits": classified, "classes": classes, "c2_reasons": why_c2}


def cmd_risk(args) -> int:
    repo = pathlib.Path(args.repo).resolve()
    cfg, qs = repo_config(repo, args.config)
    if qs or cfg is None:
        print("FAIL the config must validate before risk coverage can be reported:")
        print_questions(qs or [f"no config_project.json in {repo}"])
        return 2
    r = report(repo, cfg, args.history)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"declared risks: {', '.join(r['declared_risks']) or 'none'}")
        print("critical paths (classified C2):")
        for p in r["critical_paths"]:
            print(f"  {p['pattern']:<40} {p['files']} tracked file(s)" + ("  STALE" if not p["files"] else ""))
        if not r["critical_paths"]:
            print("  none")
        print(f"infrastructure files (C2 by K11, whatever the config): {r['infrastructure_files']}")
        print(f"risks without paths: {', '.join(r['risks_without_paths']) or 'none'}")
        c = r["classes"]
        print(f"last {r['commits']} commit(s) classified: C0 {c['C0']}, C1 {c['C1']}, C2 {c['C2']}")
        for kind, n in sorted(r["c2_reasons"].items(), key=lambda kv: -kv[1]):
            print(f"  C2 commits with {kind}: {n}")
    bad = r["stale_paths"] or r["risks_without_paths"]
    return 1 if bad else 0
