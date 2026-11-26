"""Drive the piped-register guard over its block and allow cases.

Run it with:  python hooks/test_block_piped_register.py

Uses the default REGISTER pattern, so unset REGISTER_PATTERN before running it.
"""

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "block_piped_register.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

BLOCK = [
    "wsl -e bash tools/ci_wsl.sh 2>&1 | tail -12",
    'cmd /c "tools\\ci_local.bat" | Select-String FAIL',
    '& python "tools\\gate_format.py" --fix | Select-String "x"',
    "tail -5 <(wsl -e bash tools/ci_wsl.sh)",
    "cd repo && tools/run_gates.bat | more",
]

ALLOW = [
    "wsl -e bash tools/ci_wsl.sh > out.txt 2>&1; echo EXIT: $?; tail -6 out.txt",
    "tools/ci_local.bat > out.txt; grep FAIL out.txt | head",
    'grep -n "check_hooks" tools/ci_local.bat | head -3',
    "cat tools/ci_wsl.sh | wc -l",
    "python tools/gate_lint.py",
    "git log --oneline | head",
]


def main() -> int:
    failures = 0

    for command in BLOCK:
        if not guard.offending(command):
            print(f"NOT BLOCKED (should be): {command}")
            failures += 1

    for command in ALLOW:
        if guard.offending(command):
            print(f"BLOCKED (should not be): {command}")
            failures += 1

    print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {failures} wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
