"""Drive the hook adapter (check.py) end to end, as a tool other than Claude Code would call it.

Run it with:  python hooks/test_check.py

Markers are assembled from pieces so this file's own edits are not refused by the guard it tests.
"""

import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE / "check.py"
MK = "TO" + "DO"


def adapter(*args, cwd=None):
    return subprocess.run([sys.executable, str(CHECK), *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


BLOCK_COMMANDS = [
    "cat > notes.txt <<'EOF'\nhello\nEOF",
    "ci_local.bat | tail -5",
    "npm install some-package-nobody-checked",
]
ALLOW_COMMANDS = [
    "ls -la",
    "python -m unittest > .ci-local/unit.log 2>&1",
]


def main() -> int:
    wrong, blocks, allows = 0, 0, 0

    def expect(result, code, label):
        nonlocal wrong
        if result.returncode != code:
            print(f"WRONG {label}: exit {result.returncode}, wanted {code}\n{result.stdout}{result.stderr}")
            wrong += 1

    for cmd in BLOCK_COMMANDS:
        expect(adapter("command", cmd), 2, f"command should be refused: {cmd!r}")
        blocks += 1
    for cmd in ALLOW_COMMANDS:
        expect(adapter("command", cmd), 0, f"command should be allowed: {cmd!r}")
        allows += 1

    r = adapter("--json", "command", BLOCK_COMMANDS[0])
    try:
        answer = json.loads(r.stdout)
        if answer.get("decision") != "block" or not answer.get("reason"):
            print(f"WRONG --json answer: {answer}")
            wrong += 1
    except json.JSONDecodeError:
        print(f"WRONG --json printed no JSON: {r.stdout!r}")
        wrong += 1

    with tempfile.TemporaryDirectory() as d:
        repo = pathlib.Path(d)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        src = repo / "app.py"
        src.write_text("x = 1\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")

        src.write_text(f"x = 1  # {MK} later\n", encoding="utf-8")
        expect(adapter("file", str(src)), 2, "an uncited marker added since HEAD")
        blocks += 1
        git(repo, "add", "-A")
        expect(adapter("staged", cwd=repo), 2, "an uncited marker in the staged change")
        blocks += 1

        src.write_text(f"x = 1  # {MK}(R-12) later\n", encoding="utf-8")
        expect(adapter("file", str(src)), 0, "a marker that cites its row")
        allows += 1
        git(repo, "add", "-A")
        expect(adapter("staged", cwd=repo), 0, "a cited marker in the staged change")
        allows += 1

        doc = repo / "notes.md"
        doc.write_text(f"{MK}: write the guide\n", encoding="utf-8")
        expect(adapter("file", str(doc)), 0, "a marker in a docs file")
        allows += 1

    # Fail closed: a hook that cannot run is never read as an allow.
    sys.path.insert(0, str(HERE))
    import check
    check.COMMAND_HOOKS = ("no_such_hook.py",)
    if check.main(["command", "ls"]) != 1:
        print("WRONG a hook that could not run was read as an allow")
        wrong += 1

    print(f"{blocks} block cases, {allows} allow cases, {wrong} wrong")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
