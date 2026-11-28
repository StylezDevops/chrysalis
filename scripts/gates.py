"""gates.toml: validate each gate and run gates or their controls (C8)."""

from __future__ import annotations

import pathlib
import re
import subprocess
import tomllib

from common import sabotaged


def load_gates(path: pathlib.Path):
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        return None, [f"cannot read {path}: {e}"]
    gates = data.get("gate", [])
    problems, ids = [], set()
    if not gates:
        problems.append("no [[gate]] entries")
    for i, g in enumerate(gates, 1):
        gid = g.get("id") or f"#{i}"
        if gid in ids:
            problems.append(f"{gid}: duplicate id")
        ids.add(gid)
        if not str(g.get("purpose", "")).strip():
            problems.append(f"{gid}: no purpose")
        kind = g.get("kind")
        if kind == "automated":
            if not str(g.get("run", "")).strip():
                problems.append(f"{gid}: automated gate has no run command")
            if g.get("pass") != "exit 0":
                problems.append(f"{gid}: pass must be \"exit 0\" (the only rule the runner reads)")
            if not str(g.get("control", "")).strip():
                problems.append(f"{gid}: automated gate has no control (a command that must fail)")
            expect = str(g.get("control_expect", "")).strip()
            if not expect:
                problems.append(f"{gid}: no control_expect (a pattern the gate's own detector prints when it "
                                "catches the planted defect; a bare non-zero exit proves nothing, R-13)")
            else:
                try:
                    re.compile(expect)
                except re.error as e:
                    problems.append(f"{gid}: control_expect is not a valid pattern ({e})")
        elif kind == "human":
            if not str(g.get("procedure", "")).strip():
                problems.append(f"{gid}: human gate has no procedure")
        else:
            problems.append(f"{gid}: kind must be \"automated\" or \"human\"")
    return gates, problems


def cmd_gates(args) -> int:
    path = pathlib.Path(args.file)
    gates, problems = load_gates(path)
    if args.action == "validate" or problems:
        for p in problems:
            print(f"FAIL {p}")
        print("gates file:", "OK" if not problems else f"{len(problems)} problem(s)")
        if problems or args.action == "validate":
            return 1 if problems else 0
    logs = pathlib.Path(".chrysalis") / "gates"
    logs.mkdir(parents=True, exist_ok=True)
    failed = 0
    for g in gates:
        if g["kind"] != "automated" or (args.only and g["id"] not in args.only):
            continue
        cmd = g["control"] if args.controls else g["run"]
        log = logs / f"{g['id']}{'-control' if args.controls else ''}.log"
        with open(log, "w", encoding="utf-8") as fh:
            code = subprocess.run(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT,
                                  timeout=g.get("timeout", 3600)).returncode
        if args.controls:
            # Red only when the control failed AND its output carries the gate's own finding for the
            # planted defect. A crash or an unrelated failure is not proof that the gate can see it.
            output = log.read_text(encoding="utf-8", errors="replace")
            found = re.search(g["control_expect"], output, re.MULTILINE) is not None
            if sabotaged("gates-ignore-control"):
                code, found = 1, True
            if code == 0:
                status = "control did not fail (exit 0)"
            elif not found:
                status = f"control did not prove the gate (exit {code}, no match for control_expect)"
            else:
                status = f"CONTROL RED (exit {code}) as required"
            failed += 0 if code != 0 and found else 1
        else:
            status = "PASS" if code == 0 else f"FAIL (exit {code})"
            failed += 0 if code == 0 else 1
        print(f"{g['id']:<6} {status:<36} log: {log.as_posix()}")
    print("RESULT:", "FAIL" if failed else "OK", f"({failed} failing)")
    return 1 if failed else 0
