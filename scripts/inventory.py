"""inspect: what a repository already has, found by walking it read-only (C6)."""

from __future__ import annotations

import fnmatch
import os
import pathlib
import re
import subprocess

from common import sabotaged


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


DEFAULT_DEPTH = 3


def walk_files(repo: pathlib.Path, max_depth=DEFAULT_DEPTH, unwalked=None):
    """Relative POSIX paths up to max_depth, skipping vendored and build trees. Never opens a file.
    Directories cut off by the depth limit are appended to unwalked, so the limit is reported, not silent."""
    out = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = pathlib.Path(dirpath).relative_to(repo)
        depth = len(rel_dir.parts)
        kept = [d for d in dirnames if d not in SKIP_DIRS]
        if depth >= max_depth:
            if unwalked is not None:
                unwalked.extend((rel_dir / d).as_posix() for d in kept)
            kept = []
        dirnames[:] = kept
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


def inspect(repo: pathlib.Path, max_depth=DEFAULT_DEPTH) -> dict:
    unwalked = []
    files = [] if sabotaged("inspect-blind") else walk_files(repo, max_depth, unwalked)
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
        "depth_limit": max_depth,
        "dirs_not_walked": sorted(unwalked),
        "secret_like_files_skipped": sum(1 for f in files if SECRET_NAME.search(f.rsplit("/", 1)[-1])),
    }
