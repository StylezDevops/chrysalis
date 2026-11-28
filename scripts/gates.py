"""gates.toml: validate each gate and run gates or their controls (C8)."""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import signal
import subprocess
import tomllib

from common import ROOT, sabotaged

GATE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}")


DEFAULT_TIMEOUT = 3600


def run_command(cmd: str, env: dict, out, timeout: float) -> int | None:
    """Run a gate command through the shell; its exit code, or None if it ran past `timeout`. On a
    timeout the whole process tree is killed, not only the shell, so nothing keeps running."""
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, shell=True, env=env, stdout=out, stderr=subprocess.STDOUT, **kw)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        return None


def expand_home(cmd: str, home: str) -> str:
    """Replace ${CHRYSALIS_HOME} and $CHRYSALIS_HOME in a gate command with the framework's location.
    Generated gates name the framework this way instead of one machine's path. The runner expands it
    itself because Windows cmd does not, and it touches no other $ in the command."""
    return re.sub(r"\$\{CHRYSALIS_HOME\}|\$CHRYSALIS_HOME\b", lambda _: home.replace("\\", "/"), cmd)


def load_gates(path: pathlib.Path):
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        return None, [f"cannot read {path}: {e}"]
    gates = data.get("gate", [])
    problems, ids = [], set()
    # R-25: `gate = 3` or a list of non-tables crashed the runner; the shape is checked first.
    if not isinstance(gates, list) or not all(isinstance(g, dict) for g in gates):
        return None, [f"{path}: gates must be [[gate]] tables, got {type(gates).__name__}"]
    if not gates:
        problems.append("no [[gate]] entries")
    for i, g in enumerate(gates, 1):
        raw_id = g.get("id")
        gid = raw_id if isinstance(raw_id, str) and raw_id else f"gate #{i}"
        # The id names the gate's log file and is what --only selects, so it must be present and safe
        # in a file name (R-15).
        if not (isinstance(raw_id, str) and GATE_ID.fullmatch(raw_id)):
            problems.append(f"{gid}: id must be letters, digits, '_' or '-' (for example \"T1\"), got {raw_id!r}")
        if gid in ids:
            problems.append(f"{gid}: duplicate id")
        ids.add(gid)
        if not str(g.get("purpose", "")).strip():
            problems.append(f"{gid}: no purpose")
        kind = g.get("kind")
        if "timeout" in g:
            t = g["timeout"]
            if isinstance(t, bool) or not isinstance(t, (int, float)) or t <= 0:
                problems.append(f"{gid}: timeout must be a positive number of seconds, got {t!r}")
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
    # --only must name gates that exist and can run; a typo that selects nothing is a failure, not a
    # green run of zero gates (R-16).
    automated = [g for g in gates if g["kind"] == "automated"]
    if args.only:
        known = {g["id"]: g["kind"] for g in gates}
        bad = [f"{i} (no such gate)" if i not in known else f"{i} (a {known[i]} gate, not run by this command)"
               for i in args.only if known.get(i) != "automated"]
        if bad:
            for b in bad:
                print(f"FAIL --only {b}")
            print("RESULT: FAIL (selection)")
            return 1
        automated = [g for g in automated if g["id"] in args.only]
    if not automated:
        print("FAIL no automated gate selected; nothing would run")
        print("RESULT: FAIL (selection)")
        return 1
    # Each run writes to its own folder, so two runs at once never share a log file.
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = pathlib.Path(".chrysalis") / "gates" / f"run-{stamp}-{os.getpid()}"
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CHRYSALIS_HOME"] = env.get("CHRYSALIS_HOME") or str(ROOT)
    env.setdefault("PYTHONUNBUFFERED", "1")  # what a Python gate printed survives a timeout kill
    failed = 0
    for g in automated:
        cmd = expand_home(g["control"] if args.controls else g["run"], env["CHRYSALIS_HOME"])
        log = logs / f"{g['id']}{'-control' if args.controls else ''}.log"
        limit = g.get("timeout", DEFAULT_TIMEOUT)
        with open(log, "w", encoding="utf-8") as fh:
            code = run_command(cmd, env, fh, limit)
        if code is None:
            # R-19: a hang is this gate's failure, recorded with its partial output; the run goes on.
            print(f"{g['id']:<6} {f'TIMEOUT after {limit}s':<36} log: {log.as_posix()}")
            failed += 1
            continue
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
