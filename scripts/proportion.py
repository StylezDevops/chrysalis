"""Proportion (PROPORTION.md): rule grades, change classes and project adaptations.

The grade table in PROPORTION.md is the one source of each rule's grade and of what each class asks
for; this module reads it and never restates it. chrysalis.py does the git and the command line.
A class cell starting "also" adds to the class below it; one starting "none" asks for nothing.
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import pathlib
import re

GRADES = ("control", "scaled", "practice")
CLASSES = ("C0", "C1", "C2")
DEFAULT_SMALL_LINES = 20

DOC_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".adoc"}
DOC_NAMES = {"LICENSE", "LICENCE", "NOTICE", "AUTHORS", "CHANGELOG"}
MANIFEST = re.compile(
    r"(^|/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|pyproject\.toml|poetry\.lock|"
    r"uv\.lock|requirements[^/]*\.txt|Pipfile(\.lock)?|Cargo\.(toml|lock)|go\.(mod|sum)|[^/]+\.csproj|"
    r"packages\.config|pom\.xml|build\.gradle(\.kts)?|composer\.(json|lock)|Gemfile(\.lock)?|"
    r"CMakeLists\.txt|vcpkg\.json|conanfile\.(txt|py)|foundry\.toml)$")
MIGRATION = re.compile(r"(^|/)(migrations?|alembic|db/migrate|migrate)/")
MACHINERY = re.compile(
    r"(^|/)(gates\.toml|\.gitlab-ci\.yml|azure-pipelines\.yml|Jenkinsfile|\.pre-commit-config\.yaml|"
    r"\.pre-commit-hooks\.yaml)$|(^|/)(hooks|\.claude/hooks|\.githooks|\.github/workflows)/")
DECIDED = re.compile(r"\(human, (\d{4}-\d{2}-\d{2})\)")
ADAPT_KEYS = {"rule", "change", "reason", "decided", "revisit"}


# ----------------------------------------------------------------------------------- grade table
def parse_grades(method_text: str, split) -> dict:
    """{rule id: {grade, C0, C1, C2, enforced}} from the table whose header starts '| Rule | Grade'.
    `split` is chrysalis.split_row, so one Markdown row splitter serves every table (R-9)."""
    grades, header = {}, None
    for line in method_text.splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = split(line)
        if [c.lower() for c in cells[:2]] == ["rule", "grade"]:
            header = cells
            continue
        if header is None or not re.fullmatch(r"U\d+", cells[0] if cells else ""):
            continue
        cells += [""] * (6 - len(cells))
        grades[cells[0]] = {"grade": cells[1].lower(), "C0": cells[2], "C1": cells[3], "C2": cells[4],
                            "enforced": cells[5]}
    return grades


def grade_problems(grades: dict, universal_ids: list[str]) -> list[str]:
    """Every universal rule graded exactly once, with a known grade and all three class cells."""
    problems = []
    for rid in universal_ids:
        g = grades.get(rid)
        if g is None:
            problems.append(f"{rid}: no row in the Proportion grade table")
            continue
        if g["grade"] not in GRADES:
            problems.append(f"{rid}: grade {g['grade']!r} is not one of {', '.join(GRADES)}")
        for cls in CLASSES + ("enforced",):
            if not g[cls]:
                problems.append(f"{rid}: empty {cls} cell in the grade table")
        if g["grade"] == "control" and any(g[c] != "in full" for c in CLASSES):
            problems.append(f"{rid}: a control applies in full to every class")
    for rid in sorted(set(grades) - set(universal_ids)):
        problems.append(f"{rid}: graded but not a universal rule")
    return problems


def obligations(grades: dict, cls: str) -> tuple[list[tuple[str, str]], list[str]]:
    """(what to produce for this class, the controls in force). A cell starting 'none' asks for
    nothing to be produced; 'in full' marks a control, listed once by ID."""
    produce, controls = [], []
    for rid, g in sorted(grades.items(), key=lambda kv: int(kv[0][1:])):
        if g["grade"] == "control":
            controls.append(rid)
            continue
        text = ""
        for level in CLASSES[:CLASSES.index(cls) + 1]:
            cell = g[level]
            if cell.lower().startswith("none"):
                text = ""
            elif cell.lower().startswith("also ") and text:
                text = f"{text}; {cell}"
            else:
                text = cell
        if text:
            produce.append((rid, text))
    return produce, controls


# ----------------------------------------------------------------------------------- classification
def is_doc(path: str) -> bool:
    p = pathlib.PurePosixPath(path)
    return (p.suffix.lower() in DOC_SUFFIXES or p.name in DOC_NAMES) and not MANIFEST.search(path)


def classify(changes: list[dict], cfg: dict | None) -> tuple[str, list[tuple[str, str]]]:
    """Lowest class a change may take, with (class, reason) for every finding that raised it.
    Each change is {path, status ('A', 'M', 'D', 'R', ...), lines (int, or None for binary)}."""
    change_cfg = (cfg or {}).get("change") or {}
    critical = change_cfg.get("critical_paths") or []
    small = change_cfg.get("small_lines", DEFAULT_SMALL_LINES)
    live = bool(((cfg or {}).get("risk") or {}).get("live_production"))
    reasons: list[tuple[str, str]] = []
    code_lines, code_paths = 0, []
    for c in changes:
        path = c["path"]
        hit = next((g for g in critical if fnmatch.fnmatchcase(path, g)), None)
        if hit:
            reasons.append(("C2", f"{path} matches change.critical_paths entry {hit!r}"))
        elif MANIFEST.search(path):
            reasons.append(("C2", f"{path} is a dependency manifest"))
        elif MIGRATION.search(path):
            reasons.append(("C2", f"{path} is a migration"))
        elif MACHINERY.search(path):
            reasons.append(("C2", f"{path} is checking machinery (gates, hooks or CI)"))
        if is_doc(path) and not hit:
            continue
        code_paths.append(path)
        if c["status"] == "A":
            reasons.append(("C1", f"{path} is a new file"))
        if c["lines"] is None:
            reasons.append(("C1", f"{path} is a binary change"))
        else:
            code_lines += c["lines"]
    if code_lines > small:
        reasons.append(("C1", f"{code_lines} changed lines outside docs, over change.small_lines ({small})"))
    if live and code_paths:
        reasons.append(("C1", "risk.live_production holds, so only a docs-only change is C0"))
    if not changes:
        reasons.append(("C0", "no changes against the base"))
    elif not reasons:
        reasons.append(("C0", f"{code_lines} changed lines outside docs, no new file, nothing critical"
                        if code_paths else "docs only"))
    cls = max((r[0] for r in reasons), key=CLASSES.index)
    return cls, reasons


# ----------------------------------------------------------------------------------- adaptations
def adapt_questions(cfg: dict, grades: dict) -> list[str]:
    """Problems with config `adapt`, phrased as questions to the owner (U19: an unknown field is an
    error, not a no-op)."""
    entries = cfg.get("adapt")
    if entries is None:
        return []
    if not isinstance(entries, list):
        return ["adapt should be a list of adaptations. What are they?"]
    qs, seen = [], set()
    for i, e in enumerate(entries, 1):
        where = f"adapt entry {i}"
        if not isinstance(e, dict):
            qs.append(f"{where} is not an object. What does it adapt?")
            continue
        for key in sorted(set(e) - ADAPT_KEYS):
            qs.append(f"{where} has unknown field {key!r}. Is it a typo?")
        for key in sorted(ADAPT_KEYS - set(e)):
            qs.append(f"{where} has no {key!r}. What is it?")
        if any(not (isinstance(v := e.get(k), str) and v.strip()) for k in ADAPT_KEYS & set(e)):
            qs.append(f"{where} has an empty or non-text field. What should it say?")
            continue
        rid = e.get("rule")
        if rid is None:
            continue
        if rid not in grades:
            qs.append(f"{where} adapts {rid}, which is not a universal rule. Which rule is meant?")
        elif grades[rid]["grade"] == "control":
            qs.append(f"{where} adapts {rid}, a control, and controls cannot be adapted. Drop it?")
        if rid in seen:
            qs.append(f"{where} adapts {rid} a second time. Merge the two entries?")
        seen.add(rid)
        if "decided" in e and not DECIDED.search(e["decided"]):
            qs.append(f"{where} ({rid}) needs a human decision written as '(human, YYYY-MM-DD)'. Who decided?")
        if "revisit" in e:
            try:
                dt.date.fromisoformat(e["revisit"])
            except ValueError:
                qs.append(f"{where} ({rid}) revisit {e['revisit']!r} is not a YYYY-MM-DD date. When is it?")
    return qs


def adaptations(cfg: dict) -> dict:
    """{rule id: entry} for the well-formed adaptations in cfg."""
    return {e["rule"]: e for e in cfg.get("adapt") or [] if isinstance(e, dict) and "rule" in e}


def overdue(cfg: dict, today: dt.date) -> list[str]:
    out = []
    for rid, e in adaptations(cfg).items():
        try:
            if dt.date.fromisoformat(e.get("revisit", "")) < today:
                out.append(f"the adaptation of {rid} was due for revisit on {e['revisit']}")
        except ValueError:
            continue
    return out
