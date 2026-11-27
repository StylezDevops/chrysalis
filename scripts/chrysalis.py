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
  register check [--file F]       check every CLOSED register row carries its evidence
  check                           framework self-check: evidence, conditions, no copied text
  worktree new NAME [--repo R]    worktree on branch agent/NAME from the current base (U16)
  worktree finish NAME [--build-dir D]  remove it, its branch and build dir, only if merged and clean
  worktree sweep [--apply]        list (or remove) every merged agent branch and its worktree

Standard library only. Python 3.11+ (tomllib).

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
import datetime as dt
import fnmatch
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
METHOD = ROOT / "METHOD.md"
TEMPLATES = ROOT / "templates"
GUARDRAILS = ROOT / "guardrails" / "engineering-guardrails.md"


def sabotaged(name: str) -> bool:
    return os.environ.get("CHRYSALIS_SABOTAGE") == name


# ======================================================================= config validation
ENUMS = {"stage": {"new", "pre-release", "live"}, "ci.remote": {"none", "on-request", "every-push"}}
SCHEMA = {
    # path: (type, required)
    "project": (dict, True),
    "project.name": (str, True),
    "project.title": (str, False),
    "project.description": (str, True),
    "project.problem": (str, True),
    "project.users": (list, True),
    "project.objectives": (list, False),
    "stage": (str, True),
    "repo": (dict, True),
    "repo.existing": (bool, True),
    "repo.default_branch": (str, False),
    "stack": (dict, True),
    "stack.languages": (list, True),
    "stack.frameworks": (list, False),
    "stack.platforms": (list, False),
    "risk": (dict, True),
    "risk.live_production": (bool, True),
    "risk.handles_money": (bool, True),
    "risk.handles_personal_data": (bool, True),
    "risk.auth": (bool, True),
    "risk.realtime": (bool, True),
    "risk.client_engagement": (bool, True),
    "risk.mutates_data": (bool, True),
    "ci": (dict, True),
    "ci.remote": (str, True),
    "ci.local_gate": (str, False),
    "agents": (dict, True),
    "agents.max_parallel_agents": (int, True),
    "framework": (dict, False),
    "framework.path": (str, False),
    "notes": (str, False),
}
NON_EMPTY = {"project.name", "project.description", "project.problem", "project.users", "stack.languages"}


def lookup(cfg: dict, path: str):
    node = cfg
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return KeyError
        node = node[key]
    return node


def questions(cfg) -> list[str]:
    """Every missing, mistyped or contradictory field, phrased as a question to the project owner."""
    if sabotaged("validate-accepts-all"):
        return []
    if not isinstance(cfg, dict):
        return ["The config is not a JSON object. What should it contain?"]
    qs: list[str] = []

    def walk(node, prefix):
        for key, value in node.items():
            path = f"{prefix}{key}"
            if path not in SCHEMA:
                qs.append(f"Unknown field {path}. Is it a typo, or should the schema grow?")
            elif isinstance(value, dict) and SCHEMA[path][0] is dict:
                walk(value, path + ".")

    walk(cfg, "")
    for path, (typ, required) in SCHEMA.items():
        value = lookup(cfg, path)
        if value is KeyError or value is None:
            parent_missing = "." in path and not isinstance(lookup(cfg, path.rsplit(".", 1)[0]), dict)
            if required and not parent_missing:
                qs.append(f"{path} is missing. What is it?")
            continue
        ok = isinstance(value, typ) and not (typ is int and isinstance(value, bool))
        if not ok:
            qs.append(f"{path} should be {typ.__name__}, got {type(value).__name__}. What is the right value?")
            continue
        if path in NON_EMPTY and not value:
            qs.append(f"{path} is empty. What should it say?")
        if path in ENUMS and value not in ENUMS[path]:
            qs.append(f"{path} is '{value}'. Which of {sorted(ENUMS[path])} is it?")
        if typ is list and any(not isinstance(v, str) for v in value):
            qs.append(f"{path} should be a list of strings. What are the entries?")

    # Contradictions, checked only when the fields involved are well formed.
    stage = lookup(cfg, "stage")
    existing = lookup(cfg, "repo.existing")
    live = lookup(cfg, "risk.live_production")
    agents = lookup(cfg, "agents.max_parallel_agents")
    if stage == "new" and existing is True:
        qs.append("stage is 'new' but repo.existing is true. Is this a new project or an existing repository?")
    if stage == "live" and live is False:
        qs.append("stage is 'live' but risk.live_production is false. Is there a live system?")
    if live is True and stage in ("new", "pre-release"):
        qs.append(f"risk.live_production is true but stage is '{stage}'. Has the project been released?")
    if isinstance(agents, int) and not isinstance(agents, bool) and not 1 <= agents <= 8:
        qs.append(f"agents.max_parallel_agents is {agents}; it must be 1 to 8. What cap do you want?")
    # One question per path is enough; keep the first.
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def load_config(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        sys.exit(f"config not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"config is not valid JSON: {path}: {e}")


def print_questions(qs):
    for i, q in enumerate(qs, 1):
        print(f"Q{i}. {q}")


# ======================================================================= rules from METHOD.md
def parse_method(text: str):
    """Universal rules from '### Un. Title' headings, conditional rules from the K table."""
    universal = re.findall(r"(?m)^### (U\d+)\. (.+)$", text)
    conditional = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(K\d+)\s*\|\s*(.+?)\s*\|", line)
        if m:
            conditional.append((m.group(1), m.group(2).replace("`", "").strip()))
    return universal, conditional


TOKEN = re.compile(r'\s*(?:(\()|(\))|("[^"]*")|(==)|\b(and|or|not|in)\b|([A-Za-z_][\w.]*))')


class Condition:
    """A tiny parser for the K-table conditions: paths, "strings", ==, in, and, or, not, brackets."""

    def __init__(self, text: str):
        self.text = text
        self.tokens = self.tokenise(text)
        self.pos = 0
        self.tree = self.expr()
        if self.pos != len(self.tokens):
            raise ValueError(f"trailing tokens in condition: {text}")

    @staticmethod
    def tokenise(text):
        out, pos = [], 0
        text = text.strip()
        while pos < len(text):
            m = TOKEN.match(text, pos)
            if not m or m.end() == pos:
                raise ValueError(f"cannot parse condition at '{text[pos:]}': {text}")
            kinds = ["(", ")", "str", "==", "kw", "path"]
            for kind, val in zip(kinds, m.groups()):
                if val is not None:
                    out.append((kind if kind != "kw" else val, val))
            pos = m.end()
        return out

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def take(self, kind):
        if self.peek() != kind:
            raise ValueError(f"expected {kind} in condition: {self.text}")
        self.pos += 1
        return self.tokens[self.pos - 1][1]

    def expr(self):
        node = self.conj()
        while self.peek() == "or":
            self.pos += 1
            node = ("or", node, self.conj())
        return node

    def conj(self):
        node = self.neg()
        while self.peek() == "and":
            self.pos += 1
            node = ("and", node, self.neg())
        return node

    def neg(self):
        if self.peek() == "not":
            self.pos += 1
            return ("not", self.neg())
        return self.atom()

    def atom(self):
        if self.peek() == "(":
            self.pos += 1
            node = self.expr()
            self.take(")")
            return node
        if self.peek() == "str":
            s = self.take("str")[1:-1]
            self.take("in")
            return ("in", s, self.take("path"))
        path = self.take("path")
        if self.peek() == "==":
            self.pos += 1
            return ("eq", path, self.take("str")[1:-1])
        return ("truthy", path)

    def evaluate(self, cfg, node=None):
        node = node or self.tree
        op = node[0]
        if op == "or":
            return self.evaluate(cfg, node[1]) or self.evaluate(cfg, node[2])
        if op == "and":
            return self.evaluate(cfg, node[1]) and self.evaluate(cfg, node[2])
        if op == "not":
            return not self.evaluate(cfg, node[1])
        value = lookup(cfg, node[1] if op != "in" else node[2])
        value = None if value is KeyError else value
        if op == "eq":
            return value == node[2]
        if op == "in":
            return node[1] in (value or [])
        return bool(value)


def select_rules(cfg, method_text=None):
    universal, conditional = parse_method(method_text or METHOD.read_text(encoding="utf-8"))
    chosen = [(rid, title) for rid, title in universal]
    for rid, cond in conditional:
        if sabotaged("rules-ignore-conditions") or Condition(cond).evaluate(cfg):
            chosen.append((rid, cond))
    return chosen


# ======================================================================= inspect
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", "vendor", ".cache",
             "reference", "third_party", "external", "target", ".pytest_cache", ".mypy_cache"}
SECRET_NAME = re.compile(r"(?i)(^\.env($|\.)|\.env$|apikey|api_key|secret|credential|password|\.pem$|"
                         r"\.key$|\.pfx$|\.p12$|never-read)")

ASSET_PATTERNS = {
    "agent_contract": ["CLAUDE.md", "AGENTS.md", "*/AGENTS.md", ".github/copilot-instructions.md"],
    "claude_settings": [".claude/settings.json", ".claude/settings.local.json"],
    "claude_hooks": [".claude/hooks/*"],
    "claude_skills": [".claude/skills/*/SKILL.md"],
    "claude_rules": [".claude/rules/*", ".claude/register-loop.md"],
    "lusser": [".lusser/*"],
    "decisions": ["decisions/*", "docs/adr/*", "docs/decisions/*", "adr/*"],
    "register": ["*REGISTER*.md", "docs/*REGISTER*.md", "docs/register.md", "internaldocs/*REGISTER*.md"],
    "handover": ["HANDOVER*.md", "docs/HANDOVER*.md", "NEXT_SESSION*.md", "NEXT-SESSION*.md",
                 "docs/handover.md", "notes/NEXT-SESSION.md", "project/next_session.md"],
    "specs": ["specs/*", "docs/specs/*", "docs/features/*"],
    "backlog": ["docs/BACKLOG.md", "docs/backlog.md", "BACKLOG.md", "docs/backlog/*"],
    "gates": ["VERIFICATION.md", "gates.toml", "tools/ci_local.*", "tools/run_gates.*", "scripts/ci-local.sh",
              "ops/gates/*", ".githooks/pre-push"],
    "ci": [".github/workflows/*", ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile"],
    "standards": ["docs/standards/*", "ENGINEERING_GUARDRAILS.md"],
    "manifests": ["package.json", "pyproject.toml", "requirements.txt", "CMakeLists.txt", "Cargo.toml",
                  "go.mod", "composer.json", "*.csproj", "foundry.toml", "pom.xml", "build.gradle"],
}
LANG_BY_MANIFEST = {"package.json": "javascript/typescript", "pyproject.toml": "python",
                    "requirements.txt": "python", "CMakeLists.txt": "c/c++", "Cargo.toml": "rust",
                    "go.mod": "go", "composer.json": "php", ".csproj": "c#", "foundry.toml": "solidity",
                    "pom.xml": "java", "build.gradle": "java/kotlin"}


def walk_files(repo: pathlib.Path, max_depth=3):
    """Relative POSIX paths up to max_depth, skipping vendored and build trees. Never opens a file."""
    out = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = pathlib.Path(dirpath).relative_to(repo)
        depth = len(rel_dir.parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and depth < max_depth]
        for f in filenames:
            out.append((rel_dir / f).as_posix())
    return out


def git_read(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def inspect(repo: pathlib.Path) -> dict:
    files = [] if sabotaged("inspect-blind") else walk_files(repo)
    assets = {}
    for kind, patterns in ASSET_PATTERNS.items():
        # Case-sensitive on purpose: fnmatch.fnmatch folds case on Windows, which took
        # .claude/register-loop.md for a *REGISTER* file (register row R-1).
        hits = sorted({f for f in files for pat in patterns if fnmatch.fnmatchcase(f, pat)
                       and not SECRET_NAME.search(f.rsplit("/", 1)[-1])})
        if hits:
            assets[kind] = hits
    langs = sorted({lang for f in assets.get("manifests", []) for key, lang in LANG_BY_MANIFEST.items()
                    if f.endswith(key)})
    is_git = bool(git_read(repo, "rev-parse", "--git-dir"))
    worktrees = [l[9:] for l in git_read(repo, "worktree", "list", "--porcelain").splitlines()
                 if l.startswith("worktree ")] if is_git else []
    return {
        "repo": str(repo),
        "git": is_git,
        "head": git_read(repo, "rev-parse", "--short", "HEAD") if is_git else "",
        "branches": git_read(repo, "branch", "--format=%(refname:short)").splitlines() if is_git else [],
        "worktrees": worktrees,
        "remotes": sorted(set(git_read(repo, "remote").splitlines())) if is_git else [],
        "languages_detected": langs,
        "assets": assets,
        "files_seen": len(files),
        "secret_like_files_skipped": sum(1 for f in files if SECRET_NAME.search(f.rsplit("/", 1)[-1])),
    }


# ======================================================================= plan and apply
# (target, template, equivalent asset kind or None, condition rule id or None)
TARGETS = [
    ("CLAUDE.md", "CLAUDE.md", None, None),
    ("initial.md", "initial.md", None, None),
    ("docs/backlog.md", "backlog.md", "backlog", None),
    ("docs/register.md", "register.md", "register", None),
    ("docs/handover.md", "handover.md", "handover", None),
    ("docs/adr/ADR-000-template.md", "adr.md", "decisions", None),
    ("docs/standards/ready-and-done.md", "ready-and-done.md", None, None),
    ("docs/standards/change-request.md", "change-request.md", None, "K1"),
    ("docs/standards/threat-model.md", "threat-model.md", None, "K4"),
    ("docs/standards/fix-record.md", "fix-record.md", None, None),
    ("docs/standards/audit-record.md", "audit-record.md", None, None),
    ("docs/standards/change-notice.md", "change-notice.md", None, None),
    ("docs/bug-classes.md", "bug-class.md", None, None),
    ("docs/names-that-do-not-exist.md", "names-that-do-not-exist.md", None, None),
    ("docs/verification.md", "verification.md", None, None),
    ("docs/runbook.md", "runbook.md", None, "K3"),
    ("gates.toml", "gates.toml", "gates", None),
    (".lusser/spec.md", "lusser/spec.md", "lusser", None),
    (".lusser/parts.md", "lusser/parts.md", "lusser", None),
    (".lusser/checks.toml", "lusser/checks.toml", "lusser", None),
    (".lusser/escapes.md", "lusser/escapes.md", "lusser", None),
]


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
        "universal_rules": "\n".join(f"- {rid}: {title}" for rid, title in universal),
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


def plan(repo: pathlib.Path, cfg: dict, framework_path: str):
    inv = inspect(repo)
    rule_ids = {rid for rid, _ in select_rules(cfg)}
    actions = []
    for target, template, equivalent, needs in TARGETS:
        if needs and needs not in rule_ids:
            continue
        if sabotaged("apply-skips-initial") and target == "initial.md":
            continue
        dest = repo / target
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


def write_new(path: pathlib.Path, text: str, overwrite=False) -> bool:
    """Exclusive create: returns False and writes nothing if the path already exists."""
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
    framework_path = (cfg.get("framework") or {}).get("path") or str(ROOT)
    inv, actions = plan(repo, cfg, framework_path)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = repo / ".chrysalis" / f"run-{stamp}"
    for verb, target, note, text in actions:
        line = f"{verb} {target}" + (f" -> {note}" if note and verb == "REUSE" else "")
        if write and verb == "CREATE":
            if not write_new(repo / target, text, overwrite=sabotaged("apply-overwrites")):
                line = f"PROPOSE {target} (appeared during the run)"
                write_new(run_dir / "proposals" / target, text)
        elif write and verb == "PROPOSE":
            write_new(run_dir / "proposals" / target, text)
            line += f" -> {(run_dir / 'proposals' / target).relative_to(repo).as_posix()}"
        print(line)
    if write:
        write_new(run_dir / "inventory.json", json.dumps(inv, indent=2) + "\n")
        write_new(run_dir / "rules.txt", "\n".join(f"{r} {t}" for r, t in select_rules(cfg)) + "\n")
        write_new(run_dir / "plan.txt", "\n".join(f"{a[0]} {a[1]}" for a in actions) + "\n")
        home = pathlib.Path(args.home) if args.home else pathlib.Path.home()
        guard = home / ".claude" / "engineering-guardrails.md"
        if GUARDRAILS.exists() and write_new(guard, GUARDRAILS.read_text(encoding="utf-8")):
            print(f"CREATE {guard}")
        print(f"Run record: {run_dir.relative_to(repo).as_posix()}")
        if sabotaged("apply-stages"):
            git_run(repo, "add", "-A")
    return 0


# ======================================================================= gates
def load_gates(path: pathlib.Path):
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        return None, [f"cannot read {path}: {e}"]
    gates = data.get("gate", [])
    problems, ids = [], set()
    if not gates:
        problems.append("no [[gate]] entries")
    for i, g in enumerate(gates, 1):
        gid = g.get("id") or f"#{i}"
        if gid in ids:
            problems.append(f"{gid}: duplicate id")
        ids.add(gid)
        if not str(g.get("purpose", "")).strip():
            problems.append(f"{gid}: no purpose")
        kind = g.get("kind")
        if kind == "automated":
            if not str(g.get("run", "")).strip():
                problems.append(f"{gid}: automated gate has no run command")
            if g.get("pass") != "exit 0":
                problems.append(f"{gid}: pass must be \"exit 0\" (the only rule the runner reads)")
            if not str(g.get("control", "")).strip():
                problems.append(f"{gid}: automated gate has no control (a command that must fail)")
        elif kind == "human":
            if not str(g.get("procedure", "")).strip():
                problems.append(f"{gid}: human gate has no procedure")
        else:
            problems.append(f"{gid}: kind must be \"automated\" or \"human\"")
    return gates, problems


def cmd_gates(args) -> int:
    path = pathlib.Path(args.file)
    gates, problems = load_gates(path)
    if args.action == "validate" or problems:
        for p in problems:
            print(f"FAIL {p}")
        print("gates file:", "OK" if not problems else f"{len(problems)} problem(s)")
        if problems or args.action == "validate":
            return 1 if problems else 0
    logs = pathlib.Path(".chrysalis") / "gates"
    logs.mkdir(parents=True, exist_ok=True)
    failed = 0
    for g in gates:
        if g["kind"] != "automated" or (args.only and g["id"] not in args.only):
            continue
        cmd = g["control"] if args.controls else g["run"]
        log = logs / f"{g['id']}{'-control' if args.controls else ''}.log"
        with open(log, "w", encoding="utf-8") as fh:
            code = subprocess.run(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT,
                                  timeout=g.get("timeout", 3600)).returncode
        if args.controls:
            red = code != 0 or sabotaged("gates-ignore-control")
            status = f"CONTROL RED (exit {code}) as required" if red else "control did not fail (exit 0)"
            failed += 0 if red else 1
        else:
            status = "PASS" if code == 0 else f"FAIL (exit {code})"
            failed += 0 if code == 0 else 1
        print(f"{g['id']:<6} {status:<36} log: {log.as_posix()}")
    print("RESULT:", "FAIL" if failed else "OK", f"({failed} failing)")
    return 1 if failed else 0


# ======================================================================= register
def cmd_register(args) -> int:
    path = pathlib.Path(args.file)
    root = pathlib.Path(args.root) if args.root else path.resolve().parents[1]
    header, problems, closed = None, [], 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells + [""] * (len(header) - len(cells))))
        if row.get("state", "").upper() != "CLOSED" or sabotaged("register-skip-closed"):
            continue
        closed += 1
        rid = row.get("id") or "?"
        before, after = row.get("before", ""), row.get("after", "")
        if not before or not after:
            problems.append(f"{rid}: CLOSED without both a before and an after measurement")
        elif before == after:
            problems.append(f"{rid}: CLOSED but the measurement did not move ({before})")
        test = re.split(r"::|#", row.get("test", ""))[0].strip()
        if not test:
            problems.append(f"{rid}: CLOSED without a regression test")
        elif not (root / test).exists():
            problems.append(f"{rid}: regression test not found: {test}")
        follow = row.get("follow-up", "")
        if not re.match(r"(?i)^(gate|rule|adr|bug-class|none):\s*\S", follow):
            problems.append(f"{rid}: follow-up decision missing (gate:, rule:, adr:, bug-class: or none: reason)")
    for p in problems:
        print(f"FAIL {p}")
    print(f"register: {closed} closed row(s) checked,", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


# ======================================================================= framework self-check
def long_sentences(text, min_words=8):
    body = re.sub(r"`[^`]*`", "", text)
    parts = re.split(r"(?<=[.!?])\s+|\n", body)
    return {re.sub(r"\s+", " ", s).strip(" -*|") for s in parts if len(s.split()) >= min_words}


def house_style(text: str) -> str:
    """The vendored guardrails copy is the global file with spaced em dashes replaced: a colon after a
    bold label, a comma elsewhere. The drift check applies the same function before comparing."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\*\* \u2014 ", "**: ", text)
    return text.replace(" \u2014 ", ", ").replace("\u2014", ", ")


def cmd_check(args) -> int:
    method_path = pathlib.Path(args.method) if args.method else METHOD
    text = method_path.read_text(encoding="utf-8-sig")
    problems = []
    sections = re.split(r"(?m)^### ", text)
    for sec in sections[1:]:
        m = re.match(r"(U\d+)\.", sec)
        if m and not re.search(r"(?m)^Evidence: \S", sec) and "INFERRED" not in sec \
                and not sabotaged("check-ignores-evidence"):
            problems.append(f"{m.group(1)}: no Evidence line and not marked INFERRED")
    for line in text.splitlines():
        m = re.match(r"^\|\s*(K\d+)\s*\|(.*)\|\s*$", line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            if len(cells) < 3 or not cells[-1]:
                problems.append(f"{m.group(1)}: no evidence cell")
            try:
                Condition(cells[0].replace("`", ""))
            except ValueError as e:
                problems.append(f"{m.group(1)}: {e}")
    universal, conditional = parse_method(text)
    known = {r for r, _ in universal} | {r for r, _ in conditional}
    tdir = pathlib.Path(args.templates) if args.templates else TEMPLATES
    method_sentences = long_sentences(text)
    for t in sorted(tdir.rglob("*")):
        if not t.is_file():
            continue
        body = t.read_text(encoding="utf-8-sig")
        for s in sorted(method_sentences & long_sentences(body)):
            problems.append(f"{t.relative_to(tdir).as_posix()}: copies METHOD text: \"{s[:60]}...\"")
        for rid in sorted(set(re.findall(r"\b([UK]\d+)\b", body)) - known):
            problems.append(f"{t.relative_to(tdir).as_posix()}: cites unknown rule {rid}")
    home_copy = pathlib.Path.home() / ".claude" / "engineering-guardrails.md"
    if GUARDRAILS.exists() and home_copy.exists():
        a = GUARDRAILS.read_text(encoding="utf-8").replace("\r\n", "\n")
        b = house_style(home_copy.read_text(encoding="utf-8"))
        if a != b:
            print(f"warn: {GUARDRAILS.relative_to(ROOT).as_posix()} differs from {home_copy}; "
                  "copy the newer one over the older")
    for p in problems:
        print(f"FAIL {p}")
    print(f"framework check: {len(universal)} universal, {len(conditional)} conditional rules;",
          "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


# ======================================================================= worktrees (U16)
def git_run(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip()


def cmd_worktree(args) -> int:
    repo = pathlib.Path(args.repo).resolve()
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


# ======================================================================= main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="chrysalis", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--config", default="config_project.json")

    p = sub.add_parser("rules")
    p.add_argument("--config")
    p.add_argument("--list-conditions", action="store_true")

    p = sub.add_parser("inspect")
    p.add_argument("repo")

    for name in ("plan", "apply"):
        p = sub.add_parser(name)
        p.add_argument("repo")
        p.add_argument("--config")
        p.add_argument("--home", help="home folder for installing the guardrails file (default: yours)")

    p = sub.add_parser("gates")
    p.add_argument("action", choices=["validate", "run"])
    p.add_argument("--file", default="gates.toml")
    p.add_argument("--controls", action="store_true")
    p.add_argument("--only", nargs="*")

    p = sub.add_parser("register")
    p.add_argument("action", choices=["check"])
    p.add_argument("--file", default="docs/register.md")
    p.add_argument("--root")

    p = sub.add_parser("check")
    p.add_argument("--method")
    p.add_argument("--templates")

    p = sub.add_parser("worktree")
    p.add_argument("action", choices=["new", "finish", "sweep"])
    p.add_argument("name", nargs="?")
    p.add_argument("--build-dir", help="finish: the agent's build directory outside the worktree, removed too")
    p.add_argument("--apply", action="store_true", help="sweep: remove what it lists (default: dry run)")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", default="main")
    p.add_argument("--root", help="folder that holds the worktrees (default: <repo>-worktrees beside it)")

    args = ap.parse_args(argv)
    if args.cmd == "worktree":
        return cmd_worktree(args)

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
        print(json.dumps(inspect(pathlib.Path(args.repo).resolve()), indent=2))
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
