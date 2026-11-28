"""skills install: copy the skills without ever overwriting a different one (C18)."""

from __future__ import annotations

import pathlib
import re

from common import ROOT, sabotaged


def skill_files(src: pathlib.Path, name: str) -> dict:
    """{relative path: bytes} of a skill as it would be installed under `name`. SKILL.md's `name:` line
    is rewritten when the skill is installed under a prefix, so the tool loads it under that name."""
    out = {}
    for f in sorted(src.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts:
            continue
        data = f.read_bytes()
        if f.name == "SKILL.md" and f.parent == src and name != src.name:
            data = re.sub(rb"(?m)^name:\s*\S+", b"name: " + name.encode(), data, count=1)
        out[f.relative_to(src).as_posix()] = data
    return out


def cmd_skills(args) -> int:
    dest = pathlib.Path(args.dest) if args.dest else pathlib.Path.home() / ".claude" / "skills"
    conflicts = 0
    for src in sorted(p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()):
        name = args.prefix + src.name
        target = dest / name
        want = skill_files(src, name)
        if target.exists():
            have = {f.relative_to(target).as_posix(): f.read_bytes() for f in target.rglob("*")
                    if f.is_file() and "__pycache__" not in f.parts}
            if have == want:
                print(f"SKIP     {name} (identical)")
                continue
            if not sabotaged("skills-install-overwrites"):
                conflicts += 1
                print(f"CONFLICT {name}: {target} exists and differs; left as it is "
                      f"(use --prefix to install beside it)")
                continue
        print(f"{'INSTALL ' if args.apply else 'WOULD INSTALL'} {name} -> {target}")
        if args.apply:
            for rel, data in want.items():
                f = target / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(data)
    if not args.apply:
        print("dry run: nothing written; add --apply to install")
    if conflicts:
        print(f"{conflicts} skill(s) not installed because a different skill of the same name exists")
    return 1 if conflicts else 0
