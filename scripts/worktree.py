"""Worktrees for parallel agents: new, finish and sweep (U16, C12)."""

from __future__ import annotations

import fnmatch
import pathlib
import shutil

from common import git_run, resolve_base, sabotaged


def cmd_worktree(args) -> int:
    repo = pathlib.Path(args.repo).resolve()
    base, source = resolve_base(repo, args.base)
    if base is None:
        print(f"FAIL {source}")
        return 1
    code, out = git_run(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if code:
        print(f"FAIL base branch {base!r} ({source}) does not exist in {repo}")
        return 1
    args.base = base
    print(f"base branch: {base} ({source})")
    if args.action == "sweep":
        return worktree_sweep(repo, args.base, args.apply)
    if not args.name:
        print(f"FAIL worktree {args.action} needs a NAME")
        return 1
    branch = f"agent/{args.name}"
    root = pathlib.Path(args.root).resolve() if args.root else repo.parent / f"{repo.name}-worktrees"
    path = root / args.name
    if args.action == "new":
        code, base = git_run(repo, "rev-parse", "--short", args.base)
        if code:
            print(f"FAIL unknown base {args.base}: {base}")
            return 1
        code, out = git_run(repo, "worktree", "add", "-b", branch, str(path), args.base)
        if code:
            print(f"FAIL {out}")
            return 1
        print(f"worktree: {path}\nbranch:   {branch}\nbase:     {args.base} at {base}")
        print("Give the agent its own build directory, ports, database and temp folder. It reports its base "
              "back; it does not push or run the full gate set. `worktree finish` removes the worktree, the "
              "branch and (with --build-dir) the build directory.")
        return 0
    # finish: only a merged, clean worktree is removed, and the branch is deleted with -d (never -D).
    if not path.exists():
        print(f"FAIL no worktree at {path}")
        return 1
    build = pathlib.Path(args.build_dir).resolve() if args.build_dir else None
    if build and (build == repo or build in repo.parents or build == path or build in path.parents):
        print(f"FAIL --build-dir {build} is or contains the repo or the worktree; nothing removed")
        return 1
    code, dirty = git_run(path, "status", "--porcelain")
    if code or dirty:
        print(f"FAIL worktree has uncommitted changes; nothing removed:\n{dirty}")
        return 1
    if not sabotaged("worktree-skip-merge-check"):
        code, _ = git_run(repo, "merge-base", "--is-ancestor", branch, args.base)
        if code:
            print(f"FAIL {branch} is not merged into {args.base}; nothing removed")
            return 1
    for step in (("worktree", "remove", str(path)), ("branch", "-d" if not sabotaged("worktree-skip-merge-check")
                                                     else "-D", branch), ("worktree", "prune")):
        code, out = git_run(repo, *step)
        if code:
            print(f"FAIL git {' '.join(step)}: {out}")
            return 1
    print(f"removed worktree {path} and branch {branch}")
    if build and build.exists() and not sabotaged("worktree-keep-build-dir"):
        shutil.rmtree(build)
        print(f"removed build directory {build}")
    return 0


# Branch names agents work on: this tool's own, and the ones Claude Code's isolated subagents create.
AGENT_BRANCHES = ("agent/*", "worktree-agent-*")


def worktree_sweep(repo, base, apply) -> int:
    """Find every agent branch merged into base and remove it with its worktree. Dry run unless apply."""
    code, out = git_run(repo, "worktree", "list", "--porcelain")
    if code:
        print(f"FAIL {out}")
        return 1
    checkout = {}  # branch -> worktree path, main checkout excluded
    for block in out.split("\n\n")[1:]:
        fields = dict(l.split(" ", 1) for l in block.splitlines() if " " in l)
        if fields.get("branch", "").startswith("refs/heads/"):
            checkout[fields["branch"][11:]] = pathlib.Path(fields["worktree"])
    code, out = git_run(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    if code:
        print(f"FAIL {out}")
        return 1
    branches = [b for b in out.splitlines() if any(fnmatch.fnmatch(b, p) for p in AGENT_BRANCHES)]
    failed = removable = 0
    for b in branches:
        wt = checkout.get(b)
        merged = sabotaged("worktree-sweep-skip-merge-check") or \
            git_run(repo, "merge-base", "--is-ancestor", b, base)[0] == 0
        if not merged:
            print(f"keep    {b}: not merged into {base}")
            continue
        if wt and wt.exists():
            code, dirty = git_run(wt, "status", "--porcelain")
            if code or dirty:
                print(f"keep    {b}: worktree {wt} has uncommitted changes")
                continue
        removable += 1
        if not apply:
            print(f"remove  {b}" + (f" and worktree {wt}" if wt else ""))
            continue
        delete = "-D" if sabotaged("worktree-sweep-skip-merge-check") else "-d"
        steps = [("worktree", "remove", str(wt))] if wt and wt.exists() else []
        steps += [("worktree", "prune"), ("branch", delete, b)]
        for step in steps:
            code, out = git_run(repo, *step)
            if code:
                print(f"FAIL    {b}: git {' '.join(step)}: {out}")
                failed += 1
                break
        else:
            print(f"removed {b}" + (f" and worktree {wt}" if wt else ""))
    if not apply and removable:
        print(f"{removable} to remove; run again with --apply. Build directories outside the worktree are "
              "not touched; remove them with `worktree finish --build-dir` or by hand.")
    return 1 if failed else 0
