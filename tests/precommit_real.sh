#!/usr/bin/env bash
# Real-input check for C18: run the deferral hook through the pre-commit framework itself, from this
# repository's .pre-commit-hooks.yaml, on a throwaway project. Needs `pre-commit` on PATH (CI installs
# it); without it the script says SKIPPED and exits 3, never 0.
#   bash tests/precommit_real.sh
set -u
if ! command -v pre-commit >/dev/null 2>&1; then
  echo "SKIPPED: pre-commit is not installed"
  exit 3
fi
HOOKREPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
git init -q .
git -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m base
MK="TO""DO"

printf 'x = 1  # %s later\n' "$MK" > app.py
git add app.py
if pre-commit try-repo "$HOOKREPO" chrysalis-deferral-markers >out.txt 2>&1; then
  echo "FAIL: an uncited marker was allowed"; cat out.txt; exit 1
fi
grep -q "deferral marker" out.txt || { echo "FAIL: refused, but not by the deferral hook"; cat out.txt; exit 1; }

printf 'x = 1  # %s(R-12) later\n' "$MK" > app.py
git add app.py
if ! pre-commit try-repo "$HOOKREPO" chrysalis-deferral-markers >out.txt 2>&1; then
  echo "FAIL: a marker citing its row was refused"; cat out.txt; exit 1
fi
echo "PASS: pre-commit refuses an uncited marker and allows a cited one"
