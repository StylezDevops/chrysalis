"""Paths, the sabotage switch, git, the Markdown row splitter and the base-branch rule shared by every command."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
METHOD = ROOT / "METHOD.md"
PROPORTION = ROOT / "PROPORTION.md"
HOOKS = ROOT / "hooks"
AGENT_FILE_LIMIT = 25 * 1024  # U9: an agent-facing file over about 25 KB is a defect
TEMPLATES = ROOT / "templates"
GUARDRAILS = ROOT / "guardrails" / "engineering-guardrails.md"


def sabotaged(name: str) -> bool:
    return os.environ.get("CHRYSALIS_SABOTAGE") == name


def split_row(line: str) -> list[str]:
    """Cells of a Markdown table row. A pipe escaped as \\| or inside a `code span` stays in its cell."""
    cells, cell, i, tick = [], [], 0, 0
    text = line.strip()
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] == "|":
            cell.append("|")
            i += 2
            continue
        if ch == "`":
            run_len = len(text[i:]) - len(text[i:].lstrip("`"))
            if not tick:
                tick = run_len if text.find("`" * run_len, i + run_len) != -1 else 0
            elif run_len == tick:
                tick = 0
            cell.append("`" * run_len)
            i += run_len
            continue
        if ch == "|" and not tick:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(ch)
        i += 1
    cells.append("".join(cell).strip())
    if text.startswith("|"):
        cells = cells[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        cells = cells[:-1]
    return cells


def git_run(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip()


def resolve_base(repo: pathlib.Path, explicit: str | None) -> tuple[str | None, str]:
    """(base branch, where it came from): --base, then repo.default_branch in the repo's
    config_project.json, then "main". An unreadable config is an error, not a reason to guess (U17)."""
    if explicit:
        return explicit, "--base"
    cfg = repo / "config_project.json"
    if cfg.is_file():
        try:
            branch = (json.loads(cfg.read_text(encoding="utf-8-sig")).get("repo") or {}).get("default_branch")
        except (json.JSONDecodeError, AttributeError, OSError) as e:
            return None, f"{cfg} could not be read ({e}); pass --base or fix the config"
        if isinstance(branch, str) and branch.strip():
            return branch.strip(), "repo.default_branch in config_project.json"
    return "main", "default (no --base and no repo.default_branch in config_project.json)"


def lookup(cfg: dict, path: str):
    node = cfg
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return KeyError
        node = node[key]
    return node
