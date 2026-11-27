"""Block and allow cases for git_pre_commit.py, run against a real temporary git repository."""

import pathlib
import subprocess
import sys
import tempfile

HOOK = pathlib.Path(__file__).resolve().parent / "git_pre_commit.py"
MARK = "TO" + "DO"  # assembled so this file does not trip the deferral hook
PHRASE = "for " + "now"


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=repo,
                   check=True, capture_output=True)


def case(files_at_head, staged):
    """Exit code of the hook after committing files_at_head and staging staged."""
    with tempfile.TemporaryDirectory(prefix="precommit-test-") as d:
        repo = pathlib.Path(d)
        git(repo, "init", "-q")
        for name, text in files_at_head.items():
            (repo / name).write_text(text, encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--allow-empty", "-m", "base")
        for name, text in staged.items():
            (repo / name).write_text(text, encoding="utf-8")
        git(repo, "add", "-A")
        return subprocess.run([sys.executable, str(HOOK)], cwd=repo, capture_output=True).returncode


BLOCK = [
    ({}, {"a.py": f"x = 1  # {MARK} later\n"}),
    ({"a.py": "x = 1\n"}, {"a.py": f"x = 1\n# {PHRASE} return zero\n"}),
    ({"a.py": f"# {MARK} one\n"}, {"a.py": f"# {MARK} one\n# {MARK} two\n"}),
    ({}, {"b.ts": f"const x = 1; // {PHRASE}\n"}),
]
ALLOW = [
    ({}, {"a.py": "x = 1\n"}),
    ({"a.py": f"# {MARK} old\nx = 1\n"}, {"a.py": f"# {MARK} old\nx = 2\n"}),
    ({}, {"notes.md": f"{MARK}: a markdown note is not source\n"}),
    ({"a.py": f"# {MARK} old\n"}, {"a.py": "# done\n"}),
]

wrong = sum(case(h, s) != 1 for h, s in BLOCK) + sum(case(h, s) != 0 for h, s in ALLOW)
print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {wrong} wrong")
sys.exit(1 if wrong else 0)
