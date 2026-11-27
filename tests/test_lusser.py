"""Tests for skills/lusser/scripts/lusser.py, which shipped with none.

Each rule the checker claims to enforce (SKILL.md "Rules the checker enforces") gets a case that must
fail and a neighbour that must pass. LUSSER_PATH points the tests at another copy of the script, which
is how tests/run_all.py runs them against a sabotaged one.
"""

import importlib.util
import pathlib
import random
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import LUSSER, ROOT, tempdir  # noqa: E402

EXAMPLES = ROOT / "skills" / "lusser" / "examples"

SPEC = """# Spec: t

Budget: {budget}

## Clauses

- C1. The tool prints a greeting.
- C2. [critical] The tool never deletes a file.

## Ambiguities

- A1. Q: Which greeting?
      Resolution: {resolution}
"""
PARTS = "| # | Part | Kind | Justification | Proven |\n|---|---|---|---|---|\n" \
        "| 1 | cli.py | module | entry point | no |\n| 2 | argparse | dependency | stdlib | yes |\n"
GOOD_CHECKS = """
[[check]]
clause = "C1"
kind = "spec-test"
ref = "tests/test_greet.py"

[[check]]
clause = "C1"
kind = "property"
ref = "tests/test_greet_props.py"

[[check]]
clause = "C2"
kind = "real-input"
ref = "tests/fixtures/tree.txt"
"""


def lusser(cwd, *args):
    return subprocess.run([sys.executable, str(LUSSER), *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")


class Repo:
    def __init__(self, budget=5, resolution="Hello, world. (human, 2026-11-25)", checks=GOOD_CHECKS,
                 parts=PARTS, files=("tests/test_greet.py", "tests/test_greet_props.py", "tests/fixtures/tree.txt")):
        self.tmp = tempdir()
        self.path = pathlib.Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.path)], check=True)
        lus = self.path / ".lusser"
        lus.mkdir()
        (lus / "spec.md").write_text(SPEC.format(budget=budget, resolution=resolution), encoding="utf-8")
        (lus / "parts.md").write_text(parts, encoding="utf-8")
        (lus / "checks.toml").write_text(checks, encoding="utf-8")
        for f in files:
            (self.path / f).parent.mkdir(parents=True, exist_ok=True)
            (self.path / f).write_text("x\n", encoding="utf-8")

    def __enter__(self):
        return self.path

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Check(unittest.TestCase):
    def test_L_complete_spec_passes(self):
        with Repo() as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("RESULT: OK", r.stdout)

    def test_L_open_ambiguity_fails(self):
        for res in ("OPEN", "TBD", ""):
            with self.subTest(resolution=res), Repo(resolution=res) as d:
                r = lusser(d, "check")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("A1 has no human resolution", r.stdout)

    def test_L_model_only_coverage_fails(self):
        checks = GOOD_CHECKS.replace('kind = "spec-test"', 'kind = "model-test"').replace(
            'kind = "property"', 'kind = "model-review"')
        with Repo(checks=checks) as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("C1 covered by", r.stdout)

    def test_L_critical_clause_needs_a_strong_kind(self):
        checks = GOOD_CHECKS.replace('kind = "real-input"\nref = "tests/fixtures/tree.txt"',
                                     'kind = "spec-test"\nref = "tests/test_greet.py"')
        with Repo(checks=checks) as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("C2 is [critical]", r.stdout)

    def test_L_missing_ref_path_fails(self):
        with Repo(files=("tests/test_greet.py", "tests/test_greet_props.py")) as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("ref path not found: tests/fixtures/tree.txt", r.stdout)

    def test_L_over_budget_fails(self):
        with Repo(budget=1) as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("budget is 1", r.stdout)

    def test_L_unknown_kind_fails(self):
        with Repo(checks=GOOD_CHECKS + '\n[[check]]\nclause = "C1"\nkind = "vibes"\nref = "x"\n') as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("unknown kind 'vibes'", r.stdout)

    def test_L_check_against_unknown_clause_fails(self):
        with Repo(checks=GOOD_CHECKS + '\n[[check]]\nclause = "C9"\nkind = "human-accept"\nref = "x, 2026"\n') as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("clause 'C9' not in spec.md", r.stdout)

    def test_L_human_accept_needs_who_and_when(self):
        checks = GOOD_CHECKS + '\n[[check]]\nclause = "C2"\nkind = "human-accept"\nref = ""\n'
        with Repo(checks=checks) as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("human-accept needs who/when", r.stdout)

    def test_L_bom_prefixed_files_parse(self):
        # Register row R-4: PowerShell 5.1 `Set-Content -Encoding utf8` writes a byte-order mark, and
        # lusser rejected the file with "Invalid statement (at line 1, column 1)".
        with Repo() as d:
            for name in ("spec.md", "parts.md", "checks.toml"):
                p = d / ".lusser" / name
                p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("clauses: 2", r.stdout)

    def test_L_bad_toml_fails_cleanly(self):
        with Repo(checks="[[check]\nclause = ") as d:
            r = lusser(d, "check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("checks.toml does not parse", r.stdout)

    def test_L_shipped_examples_pass_once_their_refs_exist(self):
        for ex in sorted(p for p in EXAMPLES.iterdir() if p.is_dir()):
            with self.subTest(example=ex.name), tempdir() as d:
                d = pathlib.Path(d)
                subprocess.run(["git", "init", "-q", str(d)], check=True)
                shutil.copytree(ex, d / ".lusser")
                first = lusser(d, "check")
                self.assertEqual(first.returncode, 1, "example passed with no test files present")
                for line in first.stdout.splitlines():
                    if "ref path not found: " in line:
                        p = d / line.split("ref path not found: ", 1)[1].strip()
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.touch()
                r = lusser(d, "check")
                self.assertEqual(r.returncode, 0, r.stdout)


class Init(unittest.TestCase):
    def test_L_init_creates_the_four_files_and_never_overwrites(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            self.assertEqual(lusser(d, "init").returncode, 0)
            names = sorted(p.name for p in (d / ".lusser").iterdir())
            self.assertEqual(names, ["checks.toml", "escapes.md", "parts.md", "spec.md"])
            (d / ".lusser" / "spec.md").write_text("mine\n", encoding="utf-8")
            lusser(d, "init")
            self.assertEqual((d / ".lusser" / "spec.md").read_text(encoding="utf-8"), "mine\n")


class Parts(unittest.TestCase):
    def test_L_parts_drafts_rows_from_the_diff(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            g = ["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True)
            subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "base"], check=True)
            subprocess.run(g + ["checkout", "-q", "-b", "work"], check=True)
            (d / "package.json").write_text('{"dependencies":{"left-pad":"1.3.0"}}', encoding="utf-8")
            (d / "src").mkdir()
            (d / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            subprocess.run(g + ["add", "-A"], check=True)
            subprocess.run(g + ["commit", "-q", "-m", "work"], check=True)
            r = lusser(d, "parts", "--base", "main")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertRegex(r.stdout, r"\| 1 \| dependency change in package.json \| dependency")
            self.assertRegex(r.stdout, r"\| 2 \| src/app.py \| module")

    @staticmethod
    def trunk_repo(d, config_text):
        """A repo whose only base branch is `trunk`, with one new module on a work branch."""
        g = ["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q", "-b", "trunk", str(d)], check=True)
        subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "base"], check=True)
        subprocess.run(g + ["checkout", "-q", "-b", "work"], check=True)
        (d / "src").mkdir()
        (d / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
        if config_text is not None:
            (d / "config_project.json").write_text(config_text, encoding="utf-8")
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "work"], check=True)

    def test_L_parts_base_defaults_to_the_configured_default_branch(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            self.trunk_repo(d, '{"repo": {"default_branch": "trunk"}}')
            r = lusser(d, "parts")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r"\| src/app.py \| module")
            self.assertIn("config_project.json", r.stdout, "the output does not say where the base came from")

    def test_L_parts_explicit_base_overrides_the_config(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            self.trunk_repo(d, '{"repo": {"default_branch": "nowhere"}}')
            r = lusser(d, "parts", "--base", "trunk")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r"\| src/app.py \| module")

    def test_L_parts_unreadable_config_fails_closed(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            self.trunk_repo(d, "{not json")
            r = lusser(d, "parts")
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("config_project.json", r.stdout + r.stderr)


class Arithmetic(unittest.TestCase):
    def test_L_property_needed_p_gives_even_odds(self):
        spec = importlib.util.spec_from_file_location("lusser_mod", LUSSER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rng = random.Random(3)
        for n in [1, 2] + [rng.randint(3, 500) for _ in range(50)]:
            self.assertAlmostEqual(mod.needed_p(n, 0.5) ** n, 0.5, places=9)
        self.assertEqual(mod.needed_p(0, 0.5), 1.0)


if __name__ == "__main__":
    unittest.main()
