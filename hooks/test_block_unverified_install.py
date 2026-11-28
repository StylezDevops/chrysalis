"""Drive the unverified-install guard over its block and allow cases, in a throwaway project.

Run it with:  python hooks/test_block_unverified_install.py
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "block_unverified_install.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

BLOCK = [
    "npm install lodash",
    "npm i -D some-plugin",
    "pnpm add zod",
    "yarn add axios@1.7.0",
    "bun add hono",
    "pip install flask",
    "python -m pip install numpy==2.0",
    "uv add rich",
    "uv pip install pydantic",
    "poetry add click",
    "pipx install black",
    "cargo add serde",
    "go get github.com/acme/lib@v1.2.0",
    "gem install rails",
    "composer require monolog/monolog",
    "dotnet add package Newtonsoft.Json",
    "npm install git+https://github.com/acme/lib.git",
    "cd web && npm install evil-pkg",
    "FOO=1 npm install @scope/unknown",
    "pip install flaskk",           # a typo of nothing declared
    "pip install pyyaml",           # listed in docs/dependencies.md without a human approval
]
ALLOW = [
    "npm install",
    "npm ci",
    "npm install left-pad",          # declared in package.json
    "npm install left-pad@1.3.0",
    "pnpm install",
    "pip install -r requirements.txt",
    "pip install -e .",
    "pip install requests",          # declared in requirements.txt
    "pip install Requests==2.31",
    "pip install httpx",             # verified, with a human approval
    "npm install ./local-pkg",
    "echo npm install lodash",
    "git commit -m 'npm install lodash'",
    "npm run build",
    "ls -la",
]


def main() -> int:
    wrong = 0
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "package.json").write_text(json.dumps({"dependencies": {"left-pad": "1.3.0"}}), encoding="utf-8")
        (root / "requirements.txt").write_text("requests==2.31\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "dependencies.md").write_text(
            "| Ecosystem | Package | Evidence | Approved |\n|---|---|---|---|\n"
            "| python | httpx | PyPI, encode org, 2019, 30M downloads a month | A. Lead (human, 2026-11-28) |\n"
            "| python | pyyaml | PyPI page read | pending |\n", encoding="utf-8")
        for cmd in BLOCK:
            if guard.offending(cmd, root) is None:
                print(f"NOT BLOCKED (should be): {cmd}")
                wrong += 1
        for cmd in ALLOW:
            if guard.offending(cmd, root) is not None:
                print(f"BLOCKED (should not be): {cmd} -> {guard.offending(cmd, root)}")
                wrong += 1
        # End to end, as Claude Code calls it: JSON in, a deny decision out.
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "npm install lodash"}, "cwd": d})
        r = subprocess.run([sys.executable, str(HERE / "block_unverified_install.py")], input=payload,
                           capture_output=True, text=True)
        if '"deny"' not in r.stdout:
            print(f"WRONG end to end: {r.stdout!r} {r.stderr!r}")
            wrong += 1
    print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {wrong} wrong")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
