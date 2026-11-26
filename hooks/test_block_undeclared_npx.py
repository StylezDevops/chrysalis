"""Drive the npx guard over its block and allow cases.

Run it with:  python hooks/test_block_undeclared_npx.py

It builds a throwaway project with tsc, eslint and playwright in node_modules/.bin, so the result does
not depend on what the machine running it has installed.

The runner name is assembled from pieces so this file's own command line is not refused by the guard
it tests.
"""

import importlib.util
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "block_undeclared_npx.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

_tmp = tempfile.TemporaryDirectory()
_bin = pathlib.Path(_tmp.name) / "node_modules" / ".bin"
_bin.mkdir(parents=True)
for tool in ("tsc", "eslint", "playwright"):
    (_bin / tool).write_text("")
guard.BIN_DIRS = (_bin,)

NPX = "n" + "px"

BLOCK = [
    f"cd ui && {NPX} prettier --write src/a.tsx",
    f"{NPX} --yes prettier --check .",
    f"{NPX} -y biome format .",
    f"npm exec -- prettier --write x.ts",
    f"pnpm dlx dprint fmt",
    f"bunx prettier x",
    f"{NPX} --package=eslint eslint .",
    f"{NPX} tsc --noEmit; {NPX} prettier --write x",  # the second statement is the one refused
]

ALLOW = [
    f"cd ui && {NPX} tsc --noEmit",
    f"{NPX} eslint .",
    f"{NPX} playwright test tests/app.spec.ts --project=chromium",
    "git commit -m 'do not run prettier here'",
    f"git commit -m '{NPX} may only run what the project has installed'",
    f"git commit -q -F - <<'EOF'\n{NPX} may only run what is installed\nEOF\ngit log --oneline -1",
    "python tools/format.py --fix",
]


def main() -> int:
    failures = 0

    for command in BLOCK:
        if guard.offending(command) is None:
            print(f"NOT BLOCKED (should be): {command}")
            failures += 1

    for command in ALLOW:
        if guard.offending(command) is not None:
            print(f"BLOCKED (should not be): {command} -> {guard.offending(command)}")
            failures += 1

    print(f"{len(BLOCK)} block cases, {len(ALLOW)} allow cases, {failures} wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
