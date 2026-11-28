"""plan and apply: render the templates and create only what is absent (C4, C5, C7)."""

from __future__ import annotations

import datetime as dt
import functools
import json
import pathlib
import re

import proportion

from common import GUARDRAILS, METHOD, ROOT, TEMPLATES, git_run, sabotaged
from inventory import DEFAULT_DEPTH, inspect
from project_config import load_config, print_questions, questions
from rules import select_rules


# (target, template, equivalent asset kind or None, condition rule id or None)
TARGETS = [
    ("AGENTS.md", "AGENTS.md", None, None),
    ("CLAUDE.md", "CLAUDE.md", None, None),
    (".github/workflows/chrysalis.yml", "ci-chrysalis.yml", None, None),
    ("initial.md", "initial.md", None, None),
    ("docs/backlog.md", "backlog.md", "backlog", None),
    ("docs/register.md", "register.md", "register", None),
    ("docs/handover.md", "handover.md", "handover", None),
    ("docs/adr/ADR-000-template.md", "adr.md", "decisions", None),
    ("docs/standards/ready-and-done.md", "ready-and-done.md", None, None),
    ("docs/standards/change-request.md", "change-request.md", None, "K1"),
    ("docs/standards/threat-model.md", "threat-model.md", None, "K4"),
    ("docs/standards/infra-change.md", "infra-change.md", None, "K11"),
    ("docs/standards/fix-record.md", "fix-record.md", None, None),
    ("docs/standards/audit-record.md", "audit-record.md", None, None),
    ("docs/standards/change-notice.md", "change-notice.md", None, None),
    ("docs/bug-classes.md", "bug-class.md", None, None),
    ("docs/names-that-do-not-exist.md", "names-that-do-not-exist.md", None, None),
    ("docs/verification.md", "verification.md", None, None),
    ("docs/dependencies.md", "dependencies.md", None, None),
    ("docs/runbook.md", "runbook.md", None, "K3"),
    ("gates.toml", "gates.toml", "gates", None),
    (".lusser/spec.md", "lusser/spec.md", "lusser", None),
    (".lusser/parts.md", "lusser/parts.md", "lusser", None),
    (".lusser/checks.toml", "lusser/checks.toml", "lusser", None),
    (".lusser/escapes.md", "lusser/escapes.md", "lusser", None),
]


def adapted_note(cfg: dict, rid: str) -> str:
    e = proportion.adaptations(cfg).get(rid)
    return f" (adapted: {e['change']}; decided {e['decided']}; revisit {e['revisit']})" if e else ""


@functools.cache
def framework_ref() -> str | None:
    """The framework commit a generated CI workflow pins, so the rules it checks cannot change under
    the project without a deliberate bump (U19). None when this copy is not a git checkout."""
    code, out = git_run(ROOT, "rev-parse", "HEAD")
    return out if code == 0 and re.fullmatch(r"[0-9a-f]{40}", out) else None


WORKFLOW_TARGET = ".github/workflows/chrysalis.yml"
CI_TRIGGERS = {
    "on-request": "  workflow_dispatch:",
    "every-push": "  workflow_dispatch:\n  pull_request:\n  push:\n    branches: [{branch}]",
}


def pinned_ref(cfg: dict) -> str | None:
    """framework.ref from the config, else this checkout's commit. Never a branch: a workflow that
    tracks a moving branch checks rules nobody chose (fails closed instead of falling back to main)."""
    return ((cfg.get("framework") or {}).get("ref")) or framework_ref()


def render(template: str, cfg: dict, rules, framework_path: str) -> str:
    p = cfg["project"]
    universal = [r for r in rules if r[0].startswith("U")]
    conditional = [r for r in rules if r[0].startswith("K")]
    risks = [k.replace("_", " ") for k, v in cfg["risk"].items() if v] or ["none flagged"]
    values = {
        "name": p["name"],
        "title": p.get("title") or p["name"],
        "description": p["description"],
        "problem": p["problem"],
        "users": "\n".join(f"- {u}" for u in p["users"]),
        "objectives": "\n".join(f"- {o}" for o in p.get("objectives", [])) or "- (none given)",
        "stage": cfg["stage"],
        "languages": ", ".join(cfg["stack"]["languages"]),
        "frameworks": ", ".join(cfg["stack"].get("frameworks", [])) or "none named",
        "platforms": ", ".join(cfg["stack"].get("platforms", [])) or "none named",
        "risks": "\n".join(f"- {r}" for r in risks),
        "ci_remote": cfg["ci"]["remote"],
        "local_gate": cfg["ci"].get("local_gate") or "(not set: define it in gates.toml)",
        "max_agents": str(cfg["agents"]["max_parallel_agents"]),
        "framework_path": framework_path,
        "date": dt.date.today().isoformat(),
        "universal_rules": "\n".join(f"- {rid}: {title}" + adapted_note(cfg, rid) for rid, title in universal),
        "default_branch": (cfg.get("repo") or {}).get("default_branch") or "main",
        "framework_ref": pinned_ref(cfg) or "",
        "ci_triggers": CI_TRIGGERS.get(cfg["ci"]["remote"], "").format(
            branch=(cfg.get("repo") or {}).get("default_branch") or "main"),
        "conditional_rules": "\n".join(f"- {rid} (because `{cond}`)" for rid, cond in conditional)
                             or "- none",
    }

    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"template placeholder with no value: {key}")
        return values[key]

    out = re.sub(r"\{\{(\w+)\}\}", sub, template)
    if sabotaged("claude-md-copies-text"):
        out += "\n" + METHOD.read_text(encoding="utf-8")
    return out


def plan(repo: pathlib.Path, cfg: dict, framework_path: str, max_depth=DEFAULT_DEPTH):
    inv = inspect(repo, max_depth)
    rule_ids = {rid for rid, _ in select_rules(cfg)}
    actions = []
    for target, template, equivalent, needs in TARGETS:
        if needs and needs not in rule_ids:
            continue
        if sabotaged("apply-skips-initial") and target == "initial.md":
            continue
        dest = repo / target
        if target == WORKFLOW_TARGET:
            if cfg["ci"]["remote"] == "none":
                continue  # ci.remote none: no remote CI, so no workflow
            if not pinned_ref(cfg):
                actions.append(("REFUSE", target, "no framework commit to pin: run apply from a git checkout "
                                "of Chrysalis, or set framework.ref to a full commit SHA", None))
                continue
        why = escapes(repo, dest)
        if why:
            actions.append(("REFUSE", target, why, None))
            continue
        # Equivalents are checked before existence. On a case-insensitive filesystem docs/backlog.md
        # "exists" when the repo has docs/BACKLOG.md, and checking existence first turned a reuse into a
        # proposal (register row R-2).
        if equivalent and equivalent in inv["assets"]:
            existing = inv["assets"][equivalent]
            if equivalent == "lusser":
                # A live .lusser/ is the project's own working spec: reuse each file it has and create
                # only the missing ones; template proposals beside it are noise (register row R-3).
                match = [e for e in existing if e.lower() == target.lower()]
                if match:
                    actions.append(("REUSE", target, match[0], None))
                    continue
            else:
                exact = [e for e in existing if e.lower() == target.lower()]
                shown = exact[0] if exact else existing[0]
                more = len(existing) - 1
                actions.append(("REUSE", target, shown + (f" (+{more} more)" if more else ""), None))
                continue
        text = render((TEMPLATES / template).read_text(encoding="utf-8"), cfg, select_rules(cfg),
                      framework_path)
        if dest.exists() and not sabotaged("apply-overwrites"):
            same = dest.read_bytes().replace(b"\r\n", b"\n") == text.encode("utf-8")
            actions.append(("SKIP", target, "identical", None) if same else ("PROPOSE", target, None, text))
        else:
            actions.append(("CREATE", target, None, text))
    cfg_dest = repo / "config_project.json"
    if not cfg_dest.exists():
        actions.append(("CREATE", "config_project.json", None, json.dumps(cfg, indent=2) + "\n"))
    return inv, actions


def escapes(root: pathlib.Path, path: pathlib.Path) -> str | None:
    """Why writing `path` would land outside `root`, or None. The nearest part of the path that already
    exists is resolved, so a symlinked folder pointing elsewhere is caught before anything is created
    (R-17). Exclusive create protects an existing file; it does not protect a linked parent."""
    probe = path
    while not probe.exists() and not probe.is_symlink() and probe != probe.parent:
        probe = probe.parent
    real, base = probe.resolve(), root.resolve()
    if real == base or base in real.parents:
        return None
    shown = probe.relative_to(root).as_posix() if probe.is_relative_to(root) and probe != root else str(probe)
    return f"{shown} resolves to {real}, outside the repo"


def write_new(path: pathlib.Path, text: str, overwrite=False, root: pathlib.Path | None = None) -> bool:
    """Exclusive create: returns False and writes nothing if the path already exists. With `root`, it
    also refuses a path that resolves outside root."""
    if root is not None and escapes(root, path):
        raise RuntimeError(f"refusing to write {path}: {escapes(root, path)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w" if overwrite else "x", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return True
    except FileExistsError:
        return False


def cmd_apply(args, write: bool) -> int:
    repo = pathlib.Path(args.repo).resolve()
    cfg_path = pathlib.Path(args.config) if args.config else repo / "config_project.json"
    cfg = load_config(cfg_path)
    qs = questions(cfg)
    if qs:
        print("Open questions; nothing was written.")
        print_questions(qs)
        return 2
    if not repo.is_dir():
        print(f"not a directory: {repo}")
        return 1
    # Generated files name the framework as ${CHRYSALIS_HOME}, never this machine's path; the gate
    # runner sets it to the running copy, CI to its checkout, and a person to their own clone.
    framework_path = (cfg.get("framework") or {}).get("path") or "${CHRYSALIS_HOME}"
    inv, actions = plan(repo, cfg, framework_path, args.max_depth)
    if inv["dirs_not_walked"]:
        print(f"NOTE {len(inv['dirs_not_walked'])} folder(s) deeper than {args.max_depth} levels were not "
              f"searched for existing assets (first: {inv['dirs_not_walked'][0]}); raise --max-depth to "
              f"include them")
    home = None if args.no_home else (pathlib.Path(args.home) if args.home else pathlib.Path.home())
    guard = home / ".claude" / "engineering-guardrails.md" if home else None
    if guard and GUARDRAILS.exists() and not guard.exists() and not write:
        print(f"CREATE {guard} (outside the repo; --no-home skips it)")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = repo / ".chrysalis" / f"run-{stamp}"
    why = escapes(repo, run_dir)
    if why:
        actions.insert(0, ("REFUSE", ".chrysalis/", why, None))
    refused = [a for a in actions if a[0] == "REFUSE"]
    if refused:
        # Fail closed and whole: a plan with a write outside the repo writes nothing at all (U17).
        for _, target, reason, _ in refused:
            print(f"REFUSE {target} ({reason})")
        print("FAIL apply refused the target(s) above, so nothing was written. Fix the reason given and "
              "run it again.")
        return 1
    for verb, target, note, text in actions:
        line = f"{verb} {target}" + (f" -> {note}" if note and verb == "REUSE" else "")
        if write and verb == "CREATE":
            if not write_new(repo / target, text, overwrite=sabotaged("apply-overwrites"), root=repo):
                line = f"PROPOSE {target} (appeared during the run)"
                write_new(run_dir / "proposals" / target, text, root=repo)
        elif write and verb == "PROPOSE":
            write_new(run_dir / "proposals" / target, text, root=repo)
            line += f" -> {(run_dir / 'proposals' / target).relative_to(repo).as_posix()}"
        print(line)
    if write:
        write_new(run_dir / "inventory.json", json.dumps(inv, indent=2) + "\n", root=repo)
        write_new(run_dir / "rules.txt", "\n".join(f"{r} {t}" for r, t in select_rules(cfg)) + "\n", root=repo)
        write_new(run_dir / "plan.txt", "\n".join(f"{a[0]} {a[1]}" for a in actions) + "\n", root=repo)
        if guard and GUARDRAILS.exists() and write_new(guard, GUARDRAILS.read_text(encoding="utf-8")):
            print(f"CREATE {guard} (outside the repo; --no-home skips it)")
        print(f"Run record: {run_dir.relative_to(repo).as_posix()}")
        if sabotaged("apply-stages"):
            git_run(repo, "add", "-A")
    return 0
