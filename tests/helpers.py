"""Shared helpers for the Chrysalis tests. Standard library only."""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chrysalis.py"
LUSSER = pathlib.Path(os.environ.get("LUSSER_PATH") or ROOT / "skills" / "lusser" / "scripts" / "lusser.py")
FIXTURES = ROOT / "tests" / "fixtures"


def run(*args, cwd=None, env_extra=None, timeout=600):
    """Run chrysalis.py with the given arguments. Returns CompletedProcess with text output."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def valid_config(**overrides) -> dict:
    cfg = json.loads((FIXTURES / "config-valid.json").read_text(encoding="utf-8"))
    for dotted, value in overrides.items():
        node = cfg
        keys = dotted.split("__")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        if value is DELETE:
            node.pop(keys[-1], None)
        else:
            node[keys[-1]] = value
    return cfg


DELETE = object()


def write_config(directory: pathlib.Path, cfg: dict) -> pathlib.Path:
    path = directory / "config_project.json"
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return path


def tree_hashes(root: pathlib.Path, skip=(".git",)) -> dict:
    """sha256 of every file under root, keyed by relative POSIX path, skipping the named top dirs."""
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in skip:
            continue
        if p.is_file():
            out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def make_git_repo(directory: pathlib.Path, files: dict) -> pathlib.Path:
    """Create a git repo with the given files committed once."""
    directory.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        f = directory / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(directory)], check=True)
    subprocess.run(["git", "-C", str(directory), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(directory), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-q", "-m", "base"], check=True)
    return directory


def tempdir():
    return tempfile.TemporaryDirectory(prefix="chrysalis-test-")
