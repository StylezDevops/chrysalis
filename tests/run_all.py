"""Run every Chrysalis test, or prove the tests can fail.

  python tests/run_all.py                     all suites; exit 1 if any fails
  python tests/run_all.py --only hooks        one suite: chrysalis, governance, lusser, hooks, evidence
  python tests/run_all.py --sabotage NAME     run with one deliberate defect armed; a healthy suite
                                              exits 1 (this is the control for gate T1)
  python tests/run_all.py --sweep             arm every injection in turn; each must make a test for
                                              its named clause fail, by clause ID (gate S0)
  python tests/run_all.py --sweep --include-dud   adds an injection that changes nothing; the sweep
                                              must report it unseen and exit 1 (control for S0)

Output goes to files under .ci-local/, never through a pipe, so the exit code is the verdict (U13).
"""

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / ".ci-local"

# injection name -> (suite, clause that must be among the failures)
INJECTIONS = {
    "validate-accepts-all": ("chrysalis", "C3"),
    "rules-ignore-conditions": ("chrysalis", "C2"),
    "apply-overwrites": ("chrysalis", "C4"),
    "apply-stages": ("chrysalis", "C5"),
    "inspect-blind": ("chrysalis", "C6"),
    "apply-skips-initial": ("chrysalis", "C7"),
    "gates-ignore-control": ("chrysalis", "C8"),
    "register-skip-closed": ("chrysalis", "C9"),
    "claude-md-copies-text": ("chrysalis", "C11"),
    "worktree-skip-merge-check": ("chrysalis", "C12"),
    "worktree-keep-build-dir": ("chrysalis", "C12"),
    "worktree-sweep-skip-merge-check": ("chrysalis", "C12"),
    "check-ignores-evidence": ("chrysalis", "C1"),
    "classify-always-c0": ("governance", "C15"),
    "check-ignores-file-size": ("governance", "C15"),
    "register-ignores-dates": ("governance", "C16"),
    "doctor-skips-markers": ("governance", "C17"),
    "skills-install-overwrites": ("governance", "C18"),
    "hooks-allow-all": ("hooks", "C10"),
    "lusser-no-ambiguity": ("lusser", "L"),
}
DUD = {"dud-changes-nothing": ("chrysalis", "C4")}

HOOK_STUB = "BIN_DIRS = ()\n\ndef offending(command):\n    return None\n\nif __name__ == '__main__':\n    pass\n"


def run_unittest(modules, env, log):
    with open(log, "w", encoding="utf-8") as fh:
        code = subprocess.run([sys.executable, "-m", "unittest", "-v", *modules.split()], cwd=ROOT, env=env,
                              stdout=fh, stderr=subprocess.STDOUT).returncode
    text = log.read_text(encoding="utf-8")
    failed = set(re.findall(r"^(?:FAIL|ERROR): (test_\w+)", text, re.M))
    return code, failed


def run_hooks(env, log, hook_dir):
    failed, codes = set(), []
    with open(log, "w", encoding="utf-8") as fh:
        for test in sorted(hook_dir.glob("test_*.py")):
            code = subprocess.run([sys.executable, str(test)], cwd=ROOT, env=env, stdout=fh,
                                  stderr=subprocess.STDOUT).returncode
            codes.append(code)
            if code:
                failed.add(f"test_C10_{test.stem}")
    return (1 if any(codes) else 0), failed


def run_suite(name, sabotage=None):
    LOGS.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.pop("CHRYSALIS_SABOTAGE", None)
    tag = f"-{sabotage}" if sabotage else ""
    log = LOGS / f"{name}{tag}.log"
    tmp = None
    try:
        if sabotage and sabotage not in ("hooks-allow-all", "lusser-no-ambiguity"):
            env["CHRYSALIS_SABOTAGE"] = sabotage
        if name == "chrysalis":
            return run_unittest("tests.test_chrysalis tests.test_checks tests.test_worktrees", env, log)
        if name == "governance":
            return run_unittest("tests.test_governance tests.test_generated_ci", env, log)
        if name == "evidence":
            return run_unittest("tests.test_evidence_real", env, log)
        if name == "lusser":
            if sabotage == "lusser-no-ambiguity":
                tmp = tempfile.mkdtemp(prefix="lusser-sabotage-")
                src = (ROOT / "skills/lusser/scripts/lusser.py").read_text(encoding="utf-8")
                broken = src.replace('problems.append(f"{a} has no human resolution")', "pass")
                assert broken != src, "sabotage target moved: update run_all.py"
                (pathlib.Path(tmp) / "lusser.py").write_text(broken, encoding="utf-8")
                env["LUSSER_PATH"] = str(pathlib.Path(tmp) / "lusser.py")
            return run_unittest("tests.test_lusser", env, log)
        if name == "hooks":
            hook_dir = ROOT / "hooks"
            if sabotage == "hooks-allow-all":
                tmp = tempfile.mkdtemp(prefix="hooks-sabotage-")
                hook_dir = pathlib.Path(tmp)
                for t in (ROOT / "hooks").glob("test_*.py"):
                    shutil.copy(t, hook_dir)
                for h in (ROOT / "hooks").glob("*.py"):
                    if not h.name.startswith("test_"):
                        (hook_dir / h.name).write_text(HOOK_STUB, encoding="utf-8")
            return run_hooks(env, log, hook_dir)
        raise SystemExit(f"unknown suite {name}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


SUITES = ["chrysalis", "governance", "lusser", "hooks", "evidence"]


def verdict(code, log_text):
    """PASS, FAIL or SKIP for a suite, so a skipped test is never reported as a pass (U2, R-6)."""
    if code:
        return "FAIL"
    ran = re.search(r"^Ran (\d+) tests?", log_text, re.M)
    skipped = re.search(r"skipped=(\d+)", log_text)
    ran = int(ran.group(1)) if ran else 0
    skipped = int(skipped.group(1)) if skipped else 0
    if ran and skipped == ran:
        return "SKIP (all tests skipped)"
    if skipped:
        return f"PASS, {skipped} of {ran} skipped"
    return "PASS"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=SUITES)
    ap.add_argument("--sabotage", choices=sorted(INJECTIONS))
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--include-dud", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        table = dict(INJECTIONS, **(DUD if args.include_dud else {}))
        unseen = 0
        for name, (suite, clause) in table.items():
            if args.only and suite != args.only:
                continue
            code, failed = run_suite(suite, name)
            hit = sorted(t for t in failed if f"_{clause}_" in t)
            seen = code != 0 and bool(hit)
            unseen += 0 if seen else 1
            print(f"{'SEEN  ' if seen else 'UNSEEN'} {name:<28} needs {clause:<4} "
                  f"failed {len(failed):>2}, naming it {len(hit)}")
        print("RESULT:", "OK" if not unseen else f"FAIL ({unseen} injection(s) unseen)")
        return 1 if unseen else 0

    if args.sabotage:
        suite, clause = INJECTIONS[args.sabotage]
        code, failed = run_suite(suite, args.sabotage)
        hit = sorted(t for t in failed if f"_{clause}_" in t)
        print(f"sabotage {args.sabotage}: suite {suite} exit {code}, {len(failed)} failing test(s), "
              f"{len(hit)} naming {clause}")
        for t in hit:
            print(f"  {t}")
        return code

    total = 0
    for suite in ([args.only] if args.only else SUITES):
        code, failed = run_suite(suite)
        text = (LOGS / (suite + ".log")).read_text(encoding="utf-8", errors="replace")
        print(f"{suite:<10} {verdict(code, text)} (exit {code})"
              + (f"  failing: {', '.join(sorted(failed))}" if failed else "")
              + f"  log: {(LOGS / (suite + '.log')).relative_to(ROOT).as_posix()}")
        total += 1 if code else 0
    print("RESULT:", "OK" if not total else f"FAIL ({total} suite(s))")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
