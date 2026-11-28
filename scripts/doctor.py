"""doctor: a read-only check that a project is still on the method (C17)."""

from __future__ import annotations

import datetime as dt
import fnmatch
import pathlib
import re
import subprocess
import sys

import proportion

from common import HOOKS, ROOT, git_run, sabotaged
from gates import load_gates
from inventory import inspect
from project_config import repo_config
from register import register_problems, register_rows
from rules import select_rules


def load_hook(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def contract_rule_ids(text: str) -> set[str]:
    """Rule IDs listed under '## Rules in force' in an agent contract."""
    m = re.search(r"(?ms)^## Rules in force\s*$(.*?)(?=^## )", text + "\n## end\n")
    return set(re.findall(r"(?m)^- ([UK]\d+)\b", m.group(1))) if m else set()


def doctor_checks(repo: pathlib.Path, cfg_path: str | None, release: bool):
    """[(name, problems)] for each compliance check. Reads only; writes nothing."""
    results = []
    cfg, qs = repo_config(repo, cfg_path)
    if cfg is None and not qs:
        qs = [f"no config_project.json in {repo}"]
    if cfg is not None and not qs:
        qs = proportion.overdue(cfg, dt.date.today())
    results.append(("config and adaptations", qs))

    reg = repo / "docs" / "register.md"
    rows = []
    if reg.is_file():
        rows = register_rows(reg)
        problems, _ = register_problems(rows, repo, release=release)
    else:
        problems = [f"no register at {reg.relative_to(repo).as_posix()}"]
    results.append(("register", problems))

    guard = load_hook("block_deferral_markers")
    states = {r.get("id", ""): r.get("state", "").strip().upper() for r in rows}
    problems = []
    exempt = ((cfg or {}).get("markers") or {}).get("exempt") or []
    code, tracked = git_run(repo, "ls-files")
    if code:
        problems.append(f"git ls-files failed in {repo}: {tracked}")
        tracked = ""
    skipped = 0
    for rel in tracked.splitlines():
        if sabotaged("doctor-skips-markers") or pathlib.PurePosixPath(rel).suffix.lower() not in guard.SOURCE:
            continue
        if any(fnmatch.fnmatchcase(rel, g) for g in exempt):
            skipped += 1
            continue
        try:
            text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bare, first = guard.count(text)
        if bare:
            problems.append(f"{rel}: {bare} marker(s) cite no register row (first: {first!r}); open a row "
                            "and cite it, as in (R-12)")
        for line, cid in guard.citations(text):
            if cid not in states:
                problems.append(f"{rel}:{line}: cites {cid}, which is not in the register")
            elif states[cid] == "CLOSED":
                problems.append(f"{rel}:{line}: cites {cid}, which is CLOSED; remove the marker or reopen the row")
    results.append((f"deferral markers ({skipped} file(s) exempt by markers.exempt)" if skipped
                    else "deferral markers", problems))

    gates_file = repo / "gates.toml"
    if gates_file.is_file():
        _, problems = load_gates(gates_file)
    else:
        problems = ["no gates.toml"]
    results.append(("gates", problems))

    if (repo / ".lusser").is_dir():
        lusser = ROOT / "skills" / "lusser" / "scripts" / "lusser.py"
        r = subprocess.run([sys.executable, str(lusser), "check"], cwd=repo, capture_output=True, text=True,
                           encoding="utf-8")
        fails = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith("FAIL")]
        problems = fails or ([f"lusser check exited {r.returncode}"] if r.returncode else [])
    else:
        problems = ["no .lusser/ (C1 and C2 work needs a spec, U10)"]
    results.append(("lusser", problems))

    problems = []
    contract = next((repo / n for n in ("AGENTS.md", "CLAUDE.md") if (repo / n).is_file()), None)
    if contract is None:
        problems.append("no AGENTS.md or CLAUDE.md")
    elif cfg is not None and not qs:
        listed = contract_rule_ids(contract.read_text(encoding="utf-8-sig"))
        wanted = {rid for rid, _ in select_rules(cfg)}
        for rid in sorted(wanted - listed, key=lambda s: (s[0], int(s[1:]))):
            problems.append(f"{contract.name} does not list {rid}, which the config puts in force")
        for rid in sorted(listed - wanted, key=lambda s: (s[0], int(s[1:]))):
            problems.append(f"{contract.name} lists {rid}, which the config does not put in force")
    results.append(("agent contract", problems))

    handover = inspect(repo).get("assets", {}).get("handover")
    results.append(("handover", [] if handover else ["no handover file (U12)"]))
    return results


def cmd_doctor(args) -> int:
    repo = pathlib.Path(args.repo).resolve()
    results = doctor_checks(repo, args.config, args.release)
    for name, problems in results:
        print(f"{'PASS' if not problems else 'FAIL'}  {name}")
        for p in problems:
            print(f"      {p}")
    failed = sum(1 for _, p in results if p)
    print(f"doctor: {len(results) - failed} of {len(results)} checks pass;", "OK" if not failed else "FAIL")
    return 1 if failed else 0
