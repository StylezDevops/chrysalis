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
    "dotnet add package Contoso.Unknown",
    "npm install git+https://github.com/acme/lib.git",
    "cd web && npm install evil-pkg",
    "FOO=1 npm install @scope/unknown",
    "pip install flaskk",           # a typo of nothing declared
    "pip install pyyaml",           # listed in docs/dependencies.md without a human approval
    # R-21: an install inside a nested shell or wrapper
    'bash -c "npm install lodash"',
    "sh -c 'pip install flask'",
    "cmd /c npm install lodash",
    'powershell -Command "npm install lodash"',
    "pwsh -c 'pnpm add zod'",
    'eval "npm install lodash"',
    "env CI=1 npm install lodash",
    "nohup pip install flask",
    'bash -c "cd web && sh -c \'npm install lodash\'"',
    "powershell -EncodedCommand bnBtIGluc3RhbGwgbG9kYXNo",
    # R-22: a name that appears in a manifest but not as a dependency
    "pip install toolflag",          # a key under [tool.mytool] in pyproject.toml
    "cargo add serde",               # a feature name in Cargo.toml, not a dependency
    "gem install rails",             # commented out in the Gemfile
    "dotnet add package Contoso.Widgets",  # a <Compile Include=...>, not a PackageReference
    "go get github.com/acme/old",    # only in a replace directive
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
    'bash -c "npm install left-pad"',    # nested, but declared
    "pip install fastapi",               # declared in [project] dependencies
    "pip install pytest",                # declared in [project.optional-dependencies]
    "cargo add tokio",                   # declared in [dependencies]
    "go get github.com/acme/real@v1.0.0",  # declared in a require block
    "gem install sinatra",               # declared in the Gemfile
    "dotnet add package Newtonsoft.Json",  # declared as a PackageReference
]

PYPROJECT = """[project]
name = "demo"
dependencies = ["fastapi>=0.110"]

[project.optional-dependencies]
test = ["pytest"]

[tool.mytool]
toolflag = true
"""
CARGO = """[package]
name = "demo"

[dependencies]
tokio = "1"

[features]
serde = []
"""
GOMOD = """module example.com/demo

require (
\tgithub.com/acme/real v1.0.0
)

replace github.com/acme/old => ../old
"""
GEMFILE = """source "https://rubygems.org"
gem "sinatra"
# gem "rails"
"""
CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <Compile Include="Contoso.Widgets" />
  </ItemGroup>
</Project>
"""


def main() -> int:
    wrong = 0
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "package.json").write_text(json.dumps({"dependencies": {"left-pad": "1.3.0"}}), encoding="utf-8")
        (root / "requirements.txt").write_text("requests==2.31\n", encoding="utf-8")
        for name, text in (("pyproject.toml", PYPROJECT), ("Cargo.toml", CARGO), ("go.mod", GOMOD),
                           ("Gemfile", GEMFILE), ("demo.csproj", CSPROJ)):
            (root / name).write_text(text, encoding="utf-8")
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
