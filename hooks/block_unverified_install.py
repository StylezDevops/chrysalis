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

It reads through `bash|sh|zsh -c`, `cmd /c`, `powershell|pwsh -Command`, `eval` and the prefixes
`env`, `sudo`, `nohup`, `time`, `exec`, `nice`, to a depth of 4, and refuses an encoded PowerShell
command it cannot read. Manifests are read with format-aware parsers (JSON, TOML, go.mod directives,
csproj XML), and only their dependency sections count as a declaration.

WHAT IT DOES NOT CATCH. It is an installation guard, not a supply-chain security boundary. It does
not do the registry check itself, which needs the network and judgement (the skill does that, and a
person approves it). It does not see an install inside a script, Makefile target, alias, shell
function, command substitution (`$(...)`), `xargs` or any wrapper not listed above; a package manager
it does not know; or a manifest edited and then installed with a plain `npm install`, which a
reviewer sees in the manifest's diff. Lockfile integrity, registry provenance and dependency
confusion need their own controls.
"""

import json
import os
import pathlib
import re
import shlex
import tomllib
import xml.etree.ElementTree as ET
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
    """Whether a manifest declares `name` as a dependency. Each manifest is read with a parser for its
    format, and only its dependency sections count (R-22): a name that appears elsewhere in the file (a
    tool setting, a feature, a comment, a replace directive) is not a declaration. Anything that cannot
    be parsed counts as not declared, so a broken manifest refuses rather than allows."""
    return name in DECLARED_BY.get(ecosystem, lambda _root: set())(root)


def _text(root: pathlib.Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _toml(root: pathlib.Path, rel: str) -> dict:
    try:
        return tomllib.loads(_text(root, rel)) if (root / rel).is_file() else {}
    except tomllib.TOMLDecodeError:
        return {}


def _json(root: pathlib.Path, rel: str) -> dict:
    try:
        data = json.loads(_text(root, rel) or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _pep(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _req_name(line: str) -> str | None:
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
    return _pep(m.group(1)) if m else None


def npm_declared(root: pathlib.Path) -> set:
    pkg = _json(root, "package.json")
    keys = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
    return {k.lower() for s in keys if isinstance(pkg.get(s), dict) for k in pkg[s]}


def python_declared(root: pathlib.Path) -> set:
    names = set()
    for req in root.glob("requirements*.txt"):
        names |= {n for n in map(_req_name, _text(root, req.name).splitlines()) if n}
    py = _toml(root, "pyproject.toml")
    project = py.get("project") or {}
    specs = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        specs += list(group or [])
    for group in (py.get("dependency-groups") or {}).values():
        specs += [s for s in group or [] if isinstance(s, str)]
    tool = py.get("tool") or {}
    specs += list((tool.get("uv") or {}).get("dev-dependencies") or [])
    names |= {n for n in map(_req_name, (s for s in specs if isinstance(s, str))) if n}
    poetry = tool.get("poetry") or {}
    tables = [poetry.get("dependencies") or {}, poetry.get("dev-dependencies") or {}]
    tables += [(g or {}).get("dependencies") or {} for g in (poetry.get("group") or {}).values()]
    names |= {_pep(k) for t in tables for k in t if k.lower() != "python"}
    return names


def rust_declared(root: pathlib.Path) -> set:
    cargo = _toml(root, "Cargo.toml")
    sections = ("dependencies", "dev-dependencies", "build-dependencies")
    tables = [cargo.get(s) or {} for s in sections]
    tables += [(t or {}).get(s) or {} for t in (cargo.get("target") or {}).values() for s in sections]
    tables.append((cargo.get("workspace") or {}).get("dependencies") or {})
    return {k.lower() for t in tables for k in t}


def go_declared(root: pathlib.Path) -> set:
    names, block = set(), False
    for raw in _text(root, "go.mod").splitlines():
        line = raw.split("//", 1)[0].strip()
        if block:
            if line == ")":
                block = False
            elif line:
                names.add(line.split()[0].lower())
        elif line == "require (":
            block = True
        elif line.startswith("require "):
            names.add(line.split()[1].lower())
    return names


def ruby_declared(root: pathlib.Path) -> set:
    return {m.lower() for m in re.findall(r"""(?m)^\s*gem\s+["']([^"']+)["']""", _text(root, "Gemfile"))}


def php_declared(root: pathlib.Path) -> set:
    c = _json(root, "composer.json")
    return {k.lower() for s in ("require", "require-dev") if isinstance(c.get(s), dict) for k in c[s]}


def dotnet_declared(root: pathlib.Path) -> set:
    names = set()
    for proj in root.glob("*.csproj"):
        try:
            tree = ET.fromstring(_text(root, proj.name))
        except ET.ParseError:
            continue
        for el in tree.iter():
            if el.tag.rsplit("}", 1)[-1] == "PackageReference":
                ref = el.get("Include") or el.get("Update")
                if ref:
                    names.add(ref.lower())
    return names


DECLARED_BY = {"npm": npm_declared, "python": python_declared, "rust": rust_declared, "go": go_declared,
               "ruby": ruby_declared, "php": php_declared, "dotnet": dotnet_declared}


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


SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
PREFIXES = {"sudo", "command", "nohup", "time", "exec", "nice", "env"}


def unwrap(tokens: list[str]) -> tuple[str | None, list[str]]:
    """(inner command text, rest) when the tokens run another command through a shell or wrapper
    (R-21), else (None, tokens) with wrapper words and VAR=value settings stripped."""
    t = list(tokens)
    while t and (re.fullmatch(r"\w+=.*", t[0]) or pathlib.PurePath(t[0]).name.lower() in PREFIXES):
        t = t[1:]
    if not t:
        return None, t
    head = pathlib.PurePath(t[0]).name.lower().removesuffix(".exe")
    lowered = [a.lower() for a in t[1:]]
    if head in SHELLS and "-c" in t[1:]:
        i = t.index("-c")
        return (t[i + 1] if i + 1 < len(t) else ""), []
    if head == "cmd" and ({"/c", "/k"} & set(lowered)):
        i = next(n for n, a in enumerate(lowered, 1) if a in ("/c", "/k"))
        return " ".join(t[i + 1:]), []
    if head in ("powershell", "pwsh"):
        for flag in ("-encodedcommand", "-enc", "-e", "-ec"):
            if flag in lowered:
                return ENCODED, []
        for flag in ("-command", "-c"):
            if flag in lowered:
                i = lowered.index(flag) + 1
                return " ".join(t[i + 1:]), []
    if head == "eval":
        return " ".join(t[1:]), []
    return None, t


ENCODED = "\0encoded"


def offending(command: str, root: pathlib.Path, depth: int = 0) -> str | None:
    """The first package an install command would add without a declaration or a verified entry.
    Commands run through bash -c, sh -c, cmd /c, powershell -Command and eval are read too, to a
    depth of 4; an encoded PowerShell command cannot be read, so it is refused."""
    if depth > 4:
        return "<command nested too deeply to read>"
    for tokens in simple_commands(command):
        inner, tokens = unwrap(tokens)
        if inner == ENCODED:
            return "<an encoded PowerShell command, which cannot be checked>"
        if inner is not None:
            hit = offending(inner, root, depth + 1)
            if hit:
                return hit
            continue
        found = installer(tokens)
        if not found:
            continue
        ecosystem, args = found
        for spec in packages(args):
            name = name_of(spec, ecosystem)
            if not declared(root, ecosystem, name) and not verified(root, name):
                return spec
    return None


def simple_commands(command: str) -> list[list[str]]:
    """The command split into simple commands at ;, &&, || and |, by a lexer that respects quotes, so
    an operator inside a quoted argument (bash -c "cd web && npm install x") stays in that argument."""
    lex = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        tokens = command.split()
    groups, current = [], []
    for tok in tokens:
        if tok and set(tok) <= set(";&|"):
            if current:
                groups.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        groups.append(current)
    return groups


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
