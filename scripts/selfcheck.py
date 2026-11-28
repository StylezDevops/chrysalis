"""check: the framework's own consistency (evidence, grades, conditions, size, no copied text)."""

from __future__ import annotations

import pathlib
import re

import proportion

from common import AGENT_FILE_LIMIT, GUARDRAILS, METHOD, PACKS, PROPORTION, ROOT, TEMPLATES, sabotaged, split_row
from project_config import migration_gaps
from rules import Condition, grades, parse_method, rules_text

SOURCE_DIRS = ("scripts", "hooks", "tests", "skills")
SOURCE_LINE_LIMIT = 500  # U9: a source file over about 500 lines is a defect (R-12)


def long_sentences(text, min_words=8):
    body = re.sub(r"`[^`]*`", "", text)
    parts = re.split(r"(?<=[.!?])\s+|\n", body)
    return {re.sub(r"\s+", " ", s).strip(" -*|") for s in parts if len(s.split()) >= min_words}


def house_style(text: str) -> str:
    """The vendored guardrails copy is the global file with spaced em dashes replaced: a colon after a
    bold label, a comma elsewhere. The drift check applies the same function before comparing."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\*\* \u2014 ", "**: ", text)
    return text.replace(" \u2014 ", ", ").replace("\u2014", ", ")


def cmd_check(args) -> int:
    method_path = pathlib.Path(args.method) if args.method else METHOD
    text = method_path.read_text(encoding="utf-8-sig")
    packs_text = PACKS.read_text(encoding="utf-8-sig") if PACKS.exists() else ""
    problems = []
    sections = re.split(r"(?m)^### ", text)
    for sec in sections[1:]:
        m = re.match(r"(U\d+)\.", sec)
        if m and not re.search(r"(?m)^Evidence: \S", sec) and "INFERRED" not in sec \
                and not sabotaged("check-ignores-evidence"):
            problems.append(f"{m.group(1)}: no Evidence line and not marked INFERRED")
    for line in rules_text(text).splitlines():
        m = re.match(r"^\|\s*(K\d+)\s*\|(.*)\|\s*$", line)
        if m:
            cells = split_row(line)[1:]
            if len(cells) < 3 or not cells[-1]:
                problems.append(f"{m.group(1)}: no evidence cell")
            try:
                Condition(cells[0].replace("`", ""))
            except ValueError as e:
                problems.append(f"{m.group(1)}: {e}")
    universal, conditional = parse_method(rules_text(text))
    prop_path = pathlib.Path(args.proportion) if args.proportion else PROPORTION
    prop_text = prop_path.read_text(encoding="utf-8-sig")
    problems += proportion.grade_problems(grades(prop_text), [r for r, _ in universal])
    problems += migration_gaps()
    for name, body in ((method_path.name, text), (prop_path.name, prop_text), (PACKS.name, packs_text)):
        size = len(body.replace("\r\n", "\n").encode("utf-8"))
        if size > AGENT_FILE_LIMIT:
            problems.append(f"{name} is {size} bytes, over the {AGENT_FILE_LIMIT}-byte limit for a file "
                            "agents read every session (U9); move history or detail out")
    sources = [pathlib.Path(args.sources)] if args.sources else [ROOT / d for d in SOURCE_DIRS]
    for d in sources:
        for f in sorted(d.rglob("*.py")):
            n = f.read_text(encoding="utf-8-sig").count("\n")
            if n > SOURCE_LINE_LIMIT and not sabotaged("check-ignores-file-size"):
                problems.append(f"{f.relative_to(d.parent).as_posix()} is {n} lines, over the "
                                f"{SOURCE_LINE_LIMIT}-line limit for a source file (U9, R-12); split it by "
                                "responsibility")
    known = {r for r, _ in universal} | {r for r, _ in conditional}
    tdir = pathlib.Path(args.templates) if args.templates else TEMPLATES
    method_sentences = long_sentences(text)
    for t in sorted(tdir.rglob("*")):
        if not t.is_file():
            continue
        body = t.read_text(encoding="utf-8-sig")
        for s in sorted(method_sentences & long_sentences(body)):
            problems.append(f"{t.relative_to(tdir).as_posix()}: copies METHOD text: \"{s[:60]}...\"")
        for rid in sorted(set(re.findall(r"\b([UK]\d+)\b", body)) - known):
            problems.append(f"{t.relative_to(tdir).as_posix()}: cites unknown rule {rid}")
    home_copy = pathlib.Path.home() / ".claude" / "engineering-guardrails.md"
    if GUARDRAILS.exists() and home_copy.exists():
        a = GUARDRAILS.read_text(encoding="utf-8").replace("\r\n", "\n")
        b = house_style(home_copy.read_text(encoding="utf-8"))
        if a != b:
            print(f"warn: {GUARDRAILS.relative_to(ROOT).as_posix()} differs from {home_copy}; "
                  "copy the newer one over the older")
    for p in problems:
        print(f"FAIL {p}")
    print(f"framework check: {len(universal)} universal, {len(conditional)} conditional rules;",
          "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0
