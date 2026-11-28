"""gates.toml: validate each gate and run gates or their controls (C8)."""

from __future__ import annotations

import pathlib
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
            red = code != 0 or sabotaged("gates-ignore-control")
            status = f"CONTROL RED (exit {code}) as required" if red else "control did not fail (exit 0)"
            failed += 0 if red else 1
        else:
            status = "PASS" if code == 0 else f"FAIL (exit {code})"
            failed += 0 if code == 0 else 1
        print(f"{g['id']:<6} {status:<36} log: {log.as_posix()}")
    print("RESULT:", "FAIL" if failed else "OK", f"({failed} failing)")
    return 1 if failed else 0
