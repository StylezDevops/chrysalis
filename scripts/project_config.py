"""config_project.json: the schema, and every gap or contradiction as a question (U19)."""

from __future__ import annotations

import json
import pathlib
import sys

import proportion

from common import lookup, sabotaged
from rules import grades


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
    "change": (dict, False),
    "change.critical_paths": (list, False),
    "change.small_lines": (int, False),
    "adapt": (list, False),
    "markers": (dict, False),
    "markers.exempt": (list, False),
    "notes": (str, False),
}


NON_EMPTY = {"project.name", "project.description", "project.problem", "project.users", "stack.languages"}


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
        if typ is list and path != "adapt" and any(not isinstance(v, str) for v in value):
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
    small = lookup(cfg, "change.small_lines")
    if isinstance(small, int) and not isinstance(small, bool) and not 1 <= small <= 500:
        qs.append(f"change.small_lines is {small}; it must be 1 to 500. How many lines is a small change?")
    qs += proportion.adapt_questions(cfg, grades())
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
