#!/usr/bin/env python3
"""PreToolUse guard: a package is installed only if the project already declares it, or its check
against the registry is on record with a human's approval.

WHY THIS EXISTS. Agents name packages that do not exist, and attackers register those names with
malware ("slopsquatting"); a typo of a real name is the same door. The npm-slopsquat-guard skill says
how to check a name before it is installed, but a skill is advice. This hook makes the check a
precondition: an install command for a package the project has never had is refused until the check
is written down and a person has approved it. It generalises block_undeclared_npx.py, which covers
running a package through npx, to adding one through any package manager.

WHAT IT REFUSES. An install command that names a package which is neither declared in the project's
manifests nor listed, with `(human, YYYY-MM-DD)`, in `docs/dependencies.md`. Covered: `npm install|i
|add`, `pnpm add|install|i`, `yarn add`, `bun add|install|i`, `pip install` (also `pip3`, `python -m
pip`, `py -m pip`, `uv pip`), `uv add`, `poetry add`, `pipx install`, `cargo add|install`, `go get
|install`, `gem install`, `composer require` and `dotnet add package`. A URL, git or tarball spec
counts as a package and needs its own entry. The project root is the payload's `cwd`, then
`$CLAUDE_PROJECT_DIR`, then the current directory.

WHAT IT ALLOWS. Installing what the manifests already declare (`npm install`, `npm ci`, `pip install
-r requirements.txt`, `pip install -e .`, a declared name), a local path (`./pkg`), and any package
with a human-approved entry in `docs/dependencies.md`.

WHAT IT DOES NOT CATCH: the registry check itself, which needs the network and judgement (the skill
does that, and a person approves it); an install hidden in a script the command runs; a package
manager it does not know; and edits to a manifest followed by a plain `npm install`, which a reviewer
sees in the manifest's diff.
"""

import json
import os
import pathlib
import re
import shlex
import sys

TOOLS = {"Bash", "PowerShell"}
APPROVED = re.compile(r"\(human, \d{4}-\d{2}-\d{2}\)")
# Flags that take a value, so the value is not read as a package name.
VALUE_FLAGS = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i", "--index-url",
               "--extra-index-url", "-f", "--find-links", "-t", "--target", "--prefix", "-w", "--workspace",
               "--filter", "-C", "--dir", "--registry", "--version", "-v", "--source", "-s", "--framework",
               "--project", "--manifest-path", "--group", "-G", "--python", "-p"}


def installer(tokens: list[str]) -> tuple[str, list[str]] | None:
    """(ecosystem, argument tokens) when the tokens are an install command, else None."""
    t = list(tokens)
    while t and (re.fullmatch(r"\w+=.*", t[0]) or t[0] in ("sudo", "command")):
        t = t[1:]
    if not t:
        return None
    head = pathlib.PurePath(t[0]).name.lower().removesuffix(".exe").removesuffix(".cmd")
    if head in ("python", "python3", "py") and t[1:3] == ["-m", "pip"]:
        head, t = "pip", t[2:]
    if head == "uv" and len(t) > 1 and t[1] == "pip":
        head, t = "pip", t[1:]
    verbs = {"npm": ("npm", {"install", "i", "add", "isntall"}), "pnpm": ("npm", {"add", "install", "i"}),
             "yarn": ("npm", {"add"}), "bun": ("npm", {"add", "install", "i"}),
             "pip": ("python", {"install"}), "pip3": ("python", {"install"}), "uv": ("python", {"add"}),
             "poetry": ("python", {"add"}), "pipx": ("python", {"install"}), "cargo": ("rust", {"add", "install"}),
             "go": ("go", {"get", "install"}), "gem": ("ruby", {"install"}), "composer": ("php", {"require"})}
    if head == "dotnet" and len(t) > 2 and t[1] == "add" and "package" in t[2:4]:
        i = t.index("package", 2)
        return "dotnet", t[i + 1:]
    if head in verbs and len(t) > 1 and t[1] in verbs[head][1]:
        return verbs[head][0], t[2:]
    return None


def packages(args: list[str]) -> list[str]:
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in VALUE_FLAGS:
            skip = True
            continue
        if a.startswith("-") or a in (".", ".."):
            continue
        if a.startswith(("./", "../", "/", "~", ".\\")) or re.match(r"^[A-Za-z]:[\\/]", a):
            continue  # a local path, not a registry download
        out.append(a)
    return out


def name_of(spec: str, ecosystem: str) -> str:
    """The registry name in a spec (`left-pad@1.3.0`, `requests==2.31`, `serde@1`), lower-cased; a URL or
    git spec is returned whole, since it is its own package."""
    if re.match(r"^(git\+|https?:|git:|github:|file:)", spec) or (ecosystem == "npm" and "/" in spec
                                                                      and not spec.startswith("@")):
        return spec.lower()
    if ecosystem == "npm":
        at = spec.rfind("@")
        spec = spec[:at] if at > 0 else spec
    elif ecosystem in ("python",):
        spec = re.split(r"[<>=!~;\[ ]", spec, maxsplit=1)[0]
        return re.sub(r"[-_.]+", "-", spec).lower()
    elif ecosystem in ("rust", "go"):
        spec = spec.split("@", 1)[0]
    return spec.lower()


def declared(root: pathlib.Path, ecosystem: str, name: str) -> bool:
    def text(rel):
        try:
            return (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return ""
    if ecosystem == "npm":
        try:
            pkg = json.loads(text("package.json") or "{}")
        except json.JSONDecodeError:
            return False
        keys = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
        return any(name in {k.lower() for k in (pkg.get(s) or {})} for s in keys)
    if ecosystem == "python":
        reqs = "\n".join(text(p.name) for p in root.glob("requirements*.txt")) + "\n" + text("pyproject.toml")
        names = {re.sub(r"[-_.]+", "-", m).lower() for m in re.findall(r"(?m)^\s*[\"']?([A-Za-z0-9][\w.-]*)", reqs)}
        return name in names
    if ecosystem == "rust":
        return re.search(rf"(?m)^\s*{re.escape(name)}\s*=", text("Cargo.toml")) is not None
    if ecosystem == "go":
        return re.search(rf"(?m)^\s*(require\s+)?{re.escape(name)}\s", text("go.mod")) is not None
    if ecosystem == "ruby":
        return re.search(rf"""gem\s+["']{re.escape(name)}["']""", text("Gemfile")) is not None
    if ecosystem == "php":
        try:
            req = json.loads(text("composer.json") or "{}")
        except json.JSONDecodeError:
            return False
        return name in {k.lower() for k in {**(req.get("require") or {}), **(req.get("require-dev") or {})}}
    if ecosystem == "dotnet":
        return any(re.search(rf'Include="{re.escape(name)}"', p.read_text(encoding="utf-8", errors="replace"), re.I)
                   for p in root.glob("*.csproj"))
    return False


def verified(root: pathlib.Path, name: str) -> bool:
    """A row in docs/dependencies.md whose package cell is this name and which carries a human approval."""
    try:
        text = (root / "docs" / "dependencies.md").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    for line in text.splitlines():
        cells = [c.strip().strip("`").lower() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and APPROVED.search(line) and name in (cells[1], re.sub(r"[-_.]+", "-", cells[1])):
            return True
    return False


def offending(command: str, root: pathlib.Path) -> str | None:
    """The first package an install command would add without a declaration or a verified entry."""
    for segment in re.split(r"&&|\|\||[;|\n]", command):
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            tokens = segment.split()
        found = installer(tokens)
        if not found:
            continue
        ecosystem, args = found
        for spec in packages(args):
            name = name_of(spec, ecosystem)
            if not declared(root, ecosystem, name) and not verified(root, name):
                return spec
    return None


REASON = """Refused: `{spec}` is not declared in this project's manifests and has no verified entry in
docs/dependencies.md.

Agents invent package names, and attackers register them. Before it is installed:
1. Check the name against the registry: that it exists, who publishes it, how old it is, how widely it
   is used, and that it is the package you meant (for npm, the npm-slopsquat-guard skill has the steps).
2. Record what you found as a row in docs/dependencies.md: ecosystem, package, the evidence, and who
   approved it.
3. A human approves the row, written as (human, YYYY-MM-DD). An agent may write the evidence; it never
   writes the approval.
Then run the install again."""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in TOOLS:
        return 0
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return 0
    root = pathlib.Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    spec = offending(command, root)
    if spec is None:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": REASON.format(spec=spec)}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
