#!/usr/bin/env python3
"""lusser, keep the part count honest and the checks diverse.

Subcommands:
  init                 create .lusser/ with template files
  parts [--base <ref>] draft candidate part rows from `git diff <ref>`; the ref defaults to
                       repo.default_branch in config_project.json, else main
  check                enforce the rules; exit 1 on any failure

Standard library only. Requires Python 3.11+ (tomllib).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.exit("lusser needs Python 3.11+ (tomllib).")

LUSSER_DIR = ".lusser"
KINDS_PART = {"dependency", "external-api", "schema-change", "module",
              "interface", "config", "handoff", "rework"}
KINDS_CHECK = {"model-review", "model-test", "spec-test", "property",
               "differential", "real-input", "human-accept"}
WEAK = {"model-review", "model-test"}
CRITICAL_OK = {"real-input", "differential", "human-accept"}
PATH_KINDS = {"spec-test", "property", "real-input", "differential"}

MANIFESTS = re.compile(
    r"(^|/)(package\.json|pyproject\.toml|requirements[^/]*\.txt|Pipfile|setup\.py|"
    r"[^/]+\.csproj|Directory\.Packages\.props|packages\.config|CMakeLists\.txt|"
    r"vcpkg\.json|conanfile\.(txt|py)|Cargo\.toml|go\.mod|pom\.xml|build\.gradle(\.kts)?)$")
MIGRATIONS = re.compile(r"(^|/)(migrations?|Migrations|alembic/versions)/|\.sql$")
SOURCE_EXT = {".ts", ".tsx", ".js", ".mjs", ".cs", ".py", ".cpp", ".cc", ".cxx",
              ".h", ".hpp", ".hh", ".rs", ".go", ".java", ".kt"}
TEST_HINT = re.compile(r"(^|/)(tests?|__tests__|spec|specs|Tests?)/|\.(test|spec)\.|_test\.|test_|Tests?\.cs$")
EXPORT_RX = {
    ".ts": re.compile(r"^\+\s*export\s"), ".tsx": re.compile(r"^\+\s*export\s"),
    ".js": re.compile(r"^\+\s*(export\s|module\.exports)"), ".mjs": re.compile(r"^\+\s*export\s"),
    ".cs": re.compile(r"^\+\s*public\s+(sealed\s+|static\s+|abstract\s+|partial\s+)*(class|interface|record|struct|enum)\s+(\w+)"),
    ".py": re.compile(r"^\+(def|class)\s+(\w+)"),
    ".h": re.compile(r"^\+\s*(class|struct)\s+(\w+)"), ".hpp": re.compile(r"^\+\s*(class|struct)\s+(\w+)"),
    ".hh": re.compile(r"^\+\s*(class|struct)\s+(\w+)"),
}
CONFIG_HINT = re.compile(r"\.(env|ya?ml|json|toml|ini|config)$|appsettings|\.env\.")


def root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:
        return Path.cwd()


# ---------------------------------------------------------------- parsing
def parse_spec(text: str) -> dict:
    clauses: dict[str, dict] = {}
    ambiguities: dict[str, str | None] = {}
    budget = None
    p = 0.95
    current_amb = None
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*(C\d+)\.\s*(\[critical\])?\s*(.*)", line, re.IGNORECASE)
        if m:
            clauses[m.group(1)] = {"critical": bool(m.group(2)), "text": m.group(3).strip()}
            current_amb = None
            continue
        m = re.match(r"^\s*-\s*(A\d+)\.\s*Q:\s*(.*)", line)
        if m:
            current_amb = m.group(1)
            ambiguities[current_amb] = None
            continue
        m = re.match(r"^\s*Resolution:\s*(.*)", line)
        if m and current_amb:
            ambiguities[current_amb] = m.group(1).strip()
            continue
        m = re.match(r"^\s*Budget:\s*(\d+)", line)
        if m:
            budget = int(m.group(1))
        m = re.match(r"^\s*Assumed p:\s*([0-9.]+)", line)
        if m:
            p = float(m.group(1))
    return {"clauses": clauses, "ambiguities": ambiguities, "budget": budget, "p": p}


def parse_parts(text: str) -> list[dict]:
    parts = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"\d+", cells[0]):
            continue
        if len(cells) > 5:
            print(f"  warn: parts row #{cells[0]} has {len(cells)} cells, a '|' inside a cell shifts the Proven column; escape it as \\|")
        cells += [""] * (5 - len(cells))
        parts.append({"n": int(cells[0]), "part": cells[1], "kind": cells[2].lower(),
                      "just": cells[3], "proven": cells[4].lower().startswith("yes")})
    return parts


def parse_checks(text: str) -> list[dict]:
    data = tomllib.loads(text)
    return [dict(c) for c in data.get("check", [])]


# ---------------------------------------------------------------- check
def looks_like_path(ref: str) -> bool:
    return ("/" in ref or "\\" in ref or re.search(r"\.\w{1,5}$", ref) is not None)


def cmd_check(args) -> int:
    base = root() / LUSSER_DIR
    problems: list[str] = []
    warnings: list[str] = []

    def need(name):
        f = base / name
        if not f.exists():
            problems.append(f"missing {LUSSER_DIR}/{name}")
            return ""
        return f.read_text(encoding="utf-8-sig")

    spec = parse_spec(need("spec.md"))
    parts = parse_parts(need("parts.md"))
    try:
        checks = parse_checks(need("checks.toml") or "")
    except tomllib.TOMLDecodeError as e:
        problems.append(f"checks.toml does not parse: {e}")
        checks = []

    clauses = spec["clauses"]
    if not clauses:
        problems.append("spec.md has no clauses (lines like '- C1. ...')")

    # ambiguities
    for a, res in spec["ambiguities"].items():
        if res is None or res.upper() in {"OPEN", "TBD", ""}:
            problems.append(f"{a} has no human resolution")

    # checks
    cov: dict[str, set] = {c: set() for c in clauses}
    for i, ch in enumerate(checks, 1):
        cl, kind, ref = ch.get("clause", ""), ch.get("kind", ""), str(ch.get("ref", ""))
        if kind not in KINDS_CHECK:
            problems.append(f"check {i}: unknown kind '{kind}'")
            continue
        if cl not in clauses:
            problems.append(f"check {i}: clause '{cl}' not in spec.md")
            continue
        if kind in PATH_KINDS and looks_like_path(ref):
            path = re.split(r"::|#", ref)[0]
            if not (root() / path).exists():
                problems.append(f"check {i} ({cl} {kind}): ref path not found: {path}")
                continue
        if kind == "human-accept" and not ref.strip():
            problems.append(f"check {i} ({cl}): human-accept needs who/when in ref")
            continue
        cov[cl].add(kind)

    for cl, info in clauses.items():
        strong = cov[cl] - WEAK
        if not strong:
            have = ", ".join(sorted(cov[cl])) if cov[cl] else "nothing"
            problems.append(f"{cl} covered by {have}, needs a check that isn't a model reading/writing code")
        elif strong == {"spec-test"}:
            warnings.append(f"{cl} relies on spec-test alone; a model still wrote it, add property/real-input/differential/human-accept if it matters")
        if info["critical"] and not (cov[cl] & CRITICAL_OK):
            problems.append(f"{cl} is [critical] but has none of {sorted(CRITICAL_OK)}")

    # parts
    for pt in parts:
        if pt["kind"] not in KINDS_PART:
            warnings.append(f"part #{pt['n']} unknown kind '{pt['kind']}'")
        if not pt["just"] and pt["kind"] != "rework":
            warnings.append(f"part #{pt['n']} has no justification")
    n = len(parts)
    n_unproven = sum(1 for pt in parts if not pt["proven"])
    n_rework = sum(1 for pt in parts if pt["kind"] == "rework")
    budget, p = spec["budget"], spec["p"]
    if budget is None:
        warnings.append("spec.md has no 'Budget:' line")
    elif n > budget:
        problems.append(f"parts ledger has {n} parts, budget is {budget}, stop and ask before continuing")

    # report
    print(f"Lusser check, {root()}")
    print(f"  clauses: {len(clauses)} ({sum(1 for c in clauses.values() if c['critical'])} critical)")
    print(f"  parts:   {n} total, {n_unproven} unproven, {n_rework} rework"
          + (f", budget {budget}" if budget is not None else ""))
    if n:
        print(f"  p^n at p={p}: all parts {p ** n:.1%}   unproven only {p ** n_unproven:.1%}"
              f"   (need p>={needed_p(n, 0.5):.3%} per part for even odds)")
    print("  coverage:")
    for cl, info in clauses.items():
        kinds = ", ".join(sorted(cov[cl])) or ", "
        strong = cov[cl] - WEAK
        flag = "!" if not strong else ("~" if strong == {"spec-test"} else " ")
        crit = " [critical]" if info["critical"] else ""
        print(f"   {flag} {cl}{crit}: {kinds}")
    for w in warnings:
        print(f"  warn: {w}")
    for pr in problems:
        print(f"  FAIL: {pr}")
    print("  RESULT:", "FAIL" if problems else "OK")
    return 1 if problems else 0


def needed_p(n: int, target: float) -> float:
    return math.exp(math.log(target) / n) if n else 1.0


def resolve_base(repo: Path, explicit: str | None) -> tuple[str | None, str]:
    """(base ref, where it came from): --base, then repo.default_branch in the repo's
    config_project.json, then "main". Same order as `chrysalis.py worktree`; an unreadable
    config is an error, not a reason to guess."""
    if explicit:
        return explicit, "--base"
    cfg = repo / "config_project.json"
    if cfg.is_file():
        try:
            branch = (json.loads(cfg.read_text(encoding="utf-8-sig")).get("repo") or {}).get("default_branch")
        except (ValueError, AttributeError, OSError) as e:
            return None, f"{cfg} could not be read ({e}); pass --base or fix the config"
        if isinstance(branch, str) and branch.strip():
            return branch.strip(), "repo.default_branch in config_project.json"
    return "main", "default (no --base and no repo.default_branch in config_project.json)"


# ---------------------------------------------------------------- parts draft
def cmd_parts(args) -> int:
    r = root()
    base, source = resolve_base(r, args.base)
    if base is None:
        print(f"FAIL {source}")
        return 1
    args.base = base
    print(f"base: {base} ({source})")
    try:
        names = subprocess.run(["git", "diff", "--name-status", args.base], cwd=r,
                               capture_output=True, text=True, check=True).stdout
        diff = subprocess.run(["git", "diff", "-U0", args.base], cwd=r,
                              capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"git diff failed: {e.stderr.strip()}")

    rows: list[tuple[str, str, str]] = []  # (part, kind, note)
    changed: dict[str, str] = {}
    for line in names.splitlines():
        bits = line.split("\t")
        if len(bits) >= 2:
            changed[bits[-1]] = bits[0][0]
    for path, status in changed.items():
        if MANIFESTS.search(path):
            rows.append((f"dependency change in {path}", "dependency", "list each added package as its own part"))
        elif MIGRATIONS.search(path):
            rows.append((path, "schema-change", ""))
        elif CONFIG_HINT.search(path) and status == "A":
            rows.append((path, "config", "new config surface"))
        elif status == "A" and Path(path).suffix in SOURCE_EXT and not TEST_HINT.search(path):
            rows.append((path, "module", "new source file"))

    # exported symbols added in non-test source
    current = None
    seen: set[tuple[str, str]] = set()
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            continue
        if not current or TEST_HINT.search(current):
            continue
        rx = EXPORT_RX.get(Path(current).suffix)
        if rx and (m := rx.match(line)):
            groups = [g for g in m.groups() if g]
            sym = (groups[-1].strip() if groups else "") or line[1:].strip()[:60]
            if sym.startswith("_"):
                continue
            key = (current, sym)
            if key not in seen:
                seen.add(key)
                rows.append((f"{sym} ({current})", "interface", "new public symbol"))

    if not rows:
        print("No candidate parts found in diff.")
        return 0
    start = args.start
    print("| # | Part | Kind | Justification | Proven |")
    print("|---|------|------|---------------|--------|")
    for i, (part, kind, note) in enumerate(rows, start):
        print(f"| {i} | {part} | {kind} | {note} | no |")
    print(f"\n{len(rows)} candidate rows. This is a floor: add what the heuristics missed "
          "(external APIs, handoffs, rework); do not delete mechanical rows without saying why.\n"
          "A new file and the symbols it exports may be merged into one row if they are one part in practice.")
    return 0


# ---------------------------------------------------------------- init
TEMPLATES = {
    "spec.md": """# Spec: <title>

Budget: 10 parts
Assumed p: 0.95

## Clauses

- C1. <one testable statement of behaviour>
- C2. [critical] <clause touching money / migration / auth / destructive ops>

## Ambiguities

- A1. Q: <the two readings, concretely>
      Resolution: OPEN
""",
    "parts.md": """# Parts ledger

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
""",
    "checks.toml": """# One [[check]] per check. kinds: model-review, model-test, spec-test,
# property, differential, real-input, human-accept

# [[check]]
# clause = "C1"
# kind   = "spec-test"
# ref    = "tests/..."
""",
    "escapes.md": "# Escaped defects\n\nAppend one entry per production defect. See references/formats.md.\n",
}


def cmd_init(args) -> int:
    base = root() / LUSSER_DIR
    base.mkdir(exist_ok=True)
    for name, body in TEMPLATES.items():
        f = base / name
        if f.exists():
            print(f"exists  {f}")
        else:
            f.write_text(body, encoding="utf-8")
            print(f"created {f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="lusser", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    p = sub.add_parser("parts")
    p.add_argument("--base", help="git ref to diff against (default: repo.default_branch in "
                   "config_project.json, else main)")
    p.add_argument("--start", type=int, default=1, help="first row number")
    p.set_defaults(fn=cmd_parts)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
