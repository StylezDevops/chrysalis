"""Positive control for the lusser gate: builds a throwaway repo whose spec has an unanswered
ambiguity and runs `lusser.py check` on it. lusser must fail, so this script exits with lusser's code
and a healthy lusser makes it exit non-zero. If lusser passes here, the gate it backs is blind.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

LUSSER = pathlib.Path(os.environ.get("LUSSER_PATH")
                      or pathlib.Path(__file__).resolve().parents[1] / "skills" / "lusser" / "scripts" / "lusser.py")

SPEC = """# Spec: control

Budget: 3 parts

## Clauses

- C1. The tool prints a greeting.

## Ambiguities

- A1. Q: Which greeting?
      Resolution: OPEN
"""
CHECKS = '[[check]]\nclause = "C1"\nkind = "human-accept"\nref = "human, 2026-11-25"\n'


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lusser-control-") as d:
        d = pathlib.Path(d)
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        (d / ".lusser").mkdir()
        (d / ".lusser" / "spec.md").write_text(SPEC, encoding="utf-8")
        (d / ".lusser" / "parts.md").write_text("| # | Part | Kind | Justification | Proven |\n", encoding="utf-8")
        (d / ".lusser" / "checks.toml").write_text(CHECKS, encoding="utf-8")
        r = subprocess.run([sys.executable, str(LUSSER), "check"], cwd=d, capture_output=True, text=True,
                           encoding="utf-8")
        print(r.stdout)
        return r.returncode


if __name__ == "__main__":
    sys.exit(main())
