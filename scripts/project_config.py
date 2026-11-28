"""config_project.json: the schema, and every gap or contradiction as a question (U19)."""

from __future__ import annotations

import json
import pathlib
import re
import sys

import proportion

from common import lookup, sabotaged
from rules import grades


ENUMS = {"stage": {"new", "pre-release", "live"}, "ci.remote": {"none", "on-request", "every-push"}}
SCHEMA = {
    # path: (type, required)
    "schema_version": (int, True),
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
    "risk.infrastructure": (bool, True),
    "ci": (dict, True),
    "ci.remote": (str, True),
    "ci.local_gate": (str, False),
    "agents": (dict, True),
    "agents.max_parallel_agents": (int, True),
    "framework": (dict, False),
    "framework.path": (str, False),
    "framework.ref": (str, False),
    "change": (dict, False),
    "change.critical_paths": (list, False),
    "change.small_lines": (int, False),
    "adapt": (list, False),
    "markers": (dict, False),
    "markers.exempt": (list, False),
    "notes": (str, False),
}


NON_EMPTY = {"project.name", "project.description", "project.problem", "project.users", "stack.languages"}
# The config's own version. Raise it only with a migration from the version before in MIGRATIONS, so a
# project on an older config is moved up by `config migrate`, never broken by an upgrade; `check` fails
# on a missing step. DEPRECATED holds fields still read but going away, with what replaces each.
SCHEMA_VERSION = 1
MIGRATIONS: dict = {}
DEPRECATED: dict = {}
BLOCKING = ("invalid", "incomplete")
# Risk flags whose code must be named in change.critical_paths, so a change to it is C2 (R-18).
SENSITIVE_FLAGS = ("auth", "handles_money", "handles_personal_data", "mutates_data")


def problems(cfg) -> list[tuple[str, str]]:
    """Every problem with the config as (kind, question). Kinds: invalid (wrong type, unknown field,
    contradiction, a schema this tool cannot read), incomplete (a required decision not made yet),
    dangerous (valid, but risky enough to say so) and deprecated (still read, going away)."""
    if sabotaged("validate-accepts-all"):
        return []
    if not isinstance(cfg, dict):
        return [("invalid", "The config is not a JSON object. What should it contain?")]
    out: list[tuple[str, str]] = []

    def add(kind, text):
        if (kind, text) not in out:
            out.append((kind, text))

    version = cfg.get("schema_version")
    if isinstance(version, int) and not isinstance(version, bool):
        if version > SCHEMA_VERSION:
            add("invalid", f"schema_version is {version}, written for a newer Chrysalis than this one (schema "
                           f"{SCHEMA_VERSION}). Upgrade Chrysalis to read it.")
            return out
        if version < SCHEMA_VERSION:
            add("invalid", f"schema_version is {version}; this Chrysalis reads {SCHEMA_VERSION}. Run "
                           f"`chrysalis.py config migrate --config FILE` to bring it up to date.")
            return out

    def walk(node, prefix):
        for key, value in node.items():
            path = f"{prefix}{key}"
            if path not in SCHEMA:
                add("invalid", f"Unknown field {path}. Is it a typo, or should the schema grow?")
            elif isinstance(value, dict) and SCHEMA[path][0] is dict:
                walk(value, path + ".")

    walk(cfg, "")
    for path, (typ, required) in SCHEMA.items():
        value = lookup(cfg, path)
        if value is KeyError or value is None:
            parent_missing = "." in path and not isinstance(lookup(cfg, path.rsplit(".", 1)[0]), dict)
            if required and not parent_missing:
                add("incomplete", f"{path} is missing. What is it?")
            continue
        if path in DEPRECATED:
            add("deprecated", f"{path} is deprecated: {DEPRECATED[path]}")
        ok = isinstance(value, typ) and not (typ is int and isinstance(value, bool))
        if not ok:
            add("invalid", f"{path} should be {typ.__name__}, got {type(value).__name__}. What is the right value?")
            continue
        if path in NON_EMPTY and not value:
            add("incomplete", f"{path} is empty. What should it say?")
        if path in ENUMS and value not in ENUMS[path]:
            add("invalid", f"{path} is '{value}'. Which of {sorted(ENUMS[path])} is it?")
        if typ is list and path != "adapt" and any(not isinstance(v, str) for v in value):
            add("invalid", f"{path} should be a list of strings. What are the entries?")

    # Contradictions, checked only when the fields involved are well formed.
    stage = lookup(cfg, "stage")
    existing = lookup(cfg, "repo.existing")
    live = lookup(cfg, "risk.live_production")
    agents = lookup(cfg, "agents.max_parallel_agents")
    if stage == "new" and existing is True:
        add("invalid", "stage is 'new' but repo.existing is true. Is this a new project or an existing repository?")
    if stage == "live" and live is False:
        add("invalid", "stage is 'live' but risk.live_production is false. Is there a live system?")
    if live is True and stage in ("new", "pre-release"):
        add("invalid", f"risk.live_production is true but stage is '{stage}'. Has the project been released?")
    if isinstance(agents, int) and not isinstance(agents, bool) and not 1 <= agents <= 8:
        add("invalid", f"agents.max_parallel_agents is {agents}; it must be 1 to 8. What cap do you want?")
    ref = lookup(cfg, "framework.ref")
    if isinstance(ref, str) and not re.fullmatch(r"[0-9a-f]{40}", ref):
        add("invalid", f"framework.ref is {ref!r}; it must be a full 40-character commit SHA, so the rules CI "
                       "checks cannot move under the project. Which commit?")
    small = lookup(cfg, "change.small_lines")
    if isinstance(small, int) and not isinstance(small, bool) and not 1 <= small <= 500:
        add("invalid", f"change.small_lines is {small}; it must be 1 to 500. How many lines is a small change?")
    # A sensitive risk only raises a change's class through the paths that hold it, so the paths must be
    # named (R-18). Without them a small change to auth or payment code classified as C0.
    critical = lookup(cfg, "change.critical_paths")
    if not (isinstance(critical, list) and critical):
        for flag in SENSITIVE_FLAGS:
            if lookup(cfg, f"risk.{flag}") is True:
                add("incomplete", f"risk.{flag} is true but change.critical_paths names no paths. Which paths "
                                  f"hold that code, so a change to them is classified C2?")
    for q in proportion.adapt_questions(cfg, grades()):
        add("invalid", q)

    # Valid, but risky enough that the owner should see it every time the config is checked.
    remote = lookup(cfg, "ci.remote")
    if live is True and remote == "none":
        add("dangerous", "risk.live_production is true and ci.remote is 'none': nothing outside a developer's "
                         "machine checks a change before it can reach production.")
    for g in (lookup(cfg, "markers.exempt") if isinstance(lookup(cfg, "markers.exempt"), list) else []):
        if isinstance(g, str) and "/" not in g and g.startswith("*"):
            add("dangerous", f"markers.exempt entry {g!r} exempts every matching file in the repository from "
                             "the deferral-marker check; name the files instead.")
    if isinstance(small, int) and not isinstance(small, bool) and 100 < small <= 500:
        add("dangerous", f"change.small_lines is {small}: a C0 change of that size skips the red-first test "
                         "and the audit round a C1 change gets.")
    fpath = lookup(cfg, "framework.path")
    if isinstance(fpath, str) and (pathlib.PurePosixPath(fpath).is_absolute()
                                   or pathlib.PureWindowsPath(fpath).is_absolute()):
        add("dangerous", f"framework.path {fpath!r} is absolute, so every generated file names one machine's "
                         "path; leave it unset to use ${CHRYSALIS_HOME}.")
    if isinstance(agents, int) and not isinstance(agents, bool) and 4 < agents <= 8:
        add("dangerous", f"agents.max_parallel_agents is {agents}; above 4, parallel agents needed reconciling "
                         "in every project the method came from (U16).")
    return out


def questions(cfg) -> list[str]:
    """The problems that block: invalid and incomplete config. Warnings are left to `warnings`."""
    return [text for kind, text in problems(cfg) if kind in BLOCKING]


def warnings(cfg) -> list[tuple[str, str]]:
    return [(kind, text) for kind, text in problems(cfg) if kind not in BLOCKING]


def migrate(cfg: dict) -> tuple[dict, list[int]]:
    """Bring a config up to SCHEMA_VERSION through MIGRATIONS, one version at a time; (config, the
    versions it passed through). A version with no migration is an error, never a guess."""
    version = cfg.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"schema_version is {version!r}; a config needs a whole schema_version of 1 or more")
    if version > SCHEMA_VERSION:
        raise ValueError(f"schema_version {version} is newer than this Chrysalis ({SCHEMA_VERSION}); upgrade it")
    passed = []
    while version < SCHEMA_VERSION:
        if version not in MIGRATIONS:
            raise ValueError(f"no migration from schema {version} to {version + 1}")
        cfg = MIGRATIONS[version](dict(cfg))
        version += 1
        cfg["schema_version"] = version
        passed.append(version)
    return cfg, passed


def migration_gaps() -> list[str]:
    """What the framework self-check fails on: a schema version with no way up from it, and a deprecated
    field the schema no longer reads."""
    gaps = [f"schema_version {v} has no migration to {v + 1}" for v in range(1, SCHEMA_VERSION) if v not in MIGRATIONS]
    gaps += [f"deprecated field {p} is not in the schema" for p in DEPRECATED if p not in SCHEMA]
    return gaps


def cmd_config(args) -> int:
    """config migrate: bring a config up to this Chrysalis's schema. Prints the result by default;
    --write replaces the file, and only after the migrated config validates."""
    path = pathlib.Path(args.config)
    cfg = load_config(path)
    try:
        new, passed = migrate(cfg)
    except ValueError as e:
        print(f"FAIL {e}")
        return 1
    if not passed:
        print(f"{path}: already at schema {SCHEMA_VERSION}; nothing to migrate")
        return 0
    qs = questions(new)
    if qs:
        print(f"FAIL the migrated config (schema {SCHEMA_VERSION}) still has questions; nothing written:")
        print_questions(qs)
        return 2
    text = json.dumps(new, indent=2) + "\n"
    if args.write:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: migrated through schema {', '.join(map(str, passed))}")
    else:
        print(text, end="")
    return 0


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


def repo_config(repo: pathlib.Path, explicit: str | None):
    """(config or None, questions). A config that exists but does not validate is an error (U17)."""
    path = pathlib.Path(explicit) if explicit else repo / "config_project.json"
    if not path.is_file():
        return (None, [f"config not found: {path}"]) if explicit else (None, [])
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as e:
        return None, [f"{path} could not be read ({e})"]
    return cfg, questions(cfg)
