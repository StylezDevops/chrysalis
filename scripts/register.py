"""The defect register: row states and the evidence each needs (U3, U6, C9, C16)."""

from __future__ import annotations

import datetime as dt
import pathlib
import re

from common import sabotaged, split_row


def register_rows(path: pathlib.Path) -> list[dict]:
    """Each data row of the register table as {lowercased header: cell}."""
    header, rows = None, []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = split_row(line)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells + [""] * (len(header) - len(cells)))))
    return rows


REGISTER_STATES = ("OPEN", "CLOSED", "SCHEDULED", "ACCEPTED")
SCHEDULED_RX = re.compile(r"(?i)^scheduled:\s*([^,]*\S)\s*,\s*due\s+(\d{4}-\d{2}-\d{2})\s*,\s*(\S.*)$")
ACCEPTED_RX = re.compile(r"(?i)^accepted:\s*(.*\(human, \d{4}-\d{2}-\d{2}\))\s*,\s*revisit\s+(\d{4}-\d{2}-\d{2})"
                         r"\s*,\s*(\S.*)$")


def register_problems(rows, root: pathlib.Path, release=False, today=None):
    """(problems, count per state) for the register rows (METHOD U3, U6)."""
    today = today or dt.date.today()
    problems, counts = [], {s: 0 for s in REGISTER_STATES}

    def past(rid, label, value):
        try:
            when = dt.date.fromisoformat(value)
        except ValueError:
            problems.append(f"{rid}: {label} {value!r} is not a date")
            return
        if when < today and not sabotaged("register-ignores-dates"):
            problems.append(f"{rid}: {label} {value} has passed; fix it, or have a human record a new date")

    for row in rows:
        rid = row.get("id") or "?"
        state = row.get("state", "").strip().upper()
        follow = row.get("follow-up", "").strip()
        if state not in REGISTER_STATES:
            problems.append(f"{rid}: state {row.get('state', '')!r} is not one of {', '.join(REGISTER_STATES)}")
            continue
        counts[state] += 1
        if state == "OPEN":
            if release:
                problems.append(f"{rid}: OPEN, and an open fault blocks a release (U6)")
        elif state == "SCHEDULED":
            m = SCHEDULED_RX.match(follow)
            if not m:
                problems.append(f"{rid}: SCHEDULED needs 'scheduled: OWNER, due YYYY-MM-DD, reason' in follow-up")
            else:
                past(rid, "due date", m.group(2))
        elif state == "ACCEPTED":
            m = ACCEPTED_RX.match(follow)
            if not m:
                problems.append(f"{rid}: ACCEPTED needs 'accepted: NAME (human, YYYY-MM-DD), revisit YYYY-MM-DD, "
                                "reason' in follow-up; only a human accepts a risk")
            else:
                past(rid, "revisit date", m.group(2))
        elif not sabotaged("register-skip-closed"):
            before, after = row.get("before", ""), row.get("after", "")
            if not before or not after:
                problems.append(f"{rid}: CLOSED without both a before and an after measurement")
            elif before == after:
                problems.append(f"{rid}: CLOSED but the measurement did not move ({before})")
            test = re.split(r"::|#", row.get("test", ""))[0].strip()
            if not test:
                problems.append(f"{rid}: CLOSED without a regression test")
            elif not (root.resolve() / test).resolve().is_relative_to(root.resolve()):
                # R-24: a path that climbs out of the repo found a file elsewhere and counted.
                problems.append(f"{rid}: regression test {test} is outside the repository")
            elif not (root / test).exists():
                problems.append(f"{rid}: regression test not found: {test}")
            if not re.match(r"(?i)^(gate|rule|adr|bug-class|none):\s*\S", follow):
                problems.append(f"{rid}: follow-up decision missing (gate:, rule:, adr:, bug-class: or none: reason)")
    return problems, counts


def cmd_register(args) -> int:
    path = pathlib.Path(args.file)
    root = pathlib.Path(args.root) if args.root else path.resolve().parents[1]
    problems, counts = register_problems(register_rows(path), root, release=args.release)
    for p in problems:
        print(f"FAIL {p}")
    summary = ", ".join(f"{n} {s.lower()}" for s, n in counts.items() if n) or "no rows"
    print(f"register: {summary};", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0
