"""Spec tests for the checking commands: gates, skips reported as skips, the register, the
framework self-check and the in-work project staying unnamed.

Every test name carries the clause it proves (test_C4_...). tests/run_all.py --sweep relies on that:
each sabotage injection must make a test for its named clause fail.
"""

import pathlib
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT, git, run, tempdir, valid_config, write_config, METHOD_TEXT, long_sentences  # noqa: E402



# ------------------------------------------------------------------ C8 gates
class Gates(unittest.TestCase):
    def write(self, d, text):
        p = pathlib.Path(d) / "gates.toml"
        p.write_text(text, encoding="utf-8")
        return p

    OK = 'python -c "import sys; sys.exit(0)"'
    BAD = 'python -c "import sys; sys.exit(1)"'

    def test_C8_validate_requires_purpose_pass_and_control(self):
        with tempdir() as d:
            missing = self.write(d, f'[[gate]]\nid = "G1"\nkind = "automated"\nrun = \'{self.OK}\'\npass = "exit 0"\n')
            r = run("gates", "validate", "--file", missing)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("purpose", r.stdout)
            self.assertIn("control", r.stdout)

    def test_C8_human_gate_needs_a_procedure(self):
        with tempdir() as d:
            p = self.write(d, '[[gate]]\nid = "H1"\npurpose = "a human tries it"\nkind = "human"\n')
            r = run("gates", "validate", "--file", p)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("procedure", r.stdout)

    def test_C8_run_reports_exit_codes(self):
        with tempdir() as d:
            p = self.write(d, f'[[gate]]\nid = "G1"\npurpose = "p"\nkind = "automated"\nrun = \'{self.BAD}\'\n'
                              f'pass = "exit 0"\ncontrol = \'{self.BAD}\'\n')
            r = run("gates", "run", "--file", p, cwd=d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("G1", r.stdout)
            self.assertIn("FAIL", r.stdout)

    def test_C8_control_that_passes_is_a_failure(self):
        with tempdir() as d:
            r = run("gates", "run", "--controls", "--file", self.gate(d, self.OK), cwd=d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("control did not fail", r.stdout)

    # A control that stands in for the gate's detector: prints its finding (21) and fails.
    DETECTS = 'python -c "import sys; print(sys.version_info[0] * 7); sys.exit(1)"'

    def gate(self, d, control, expect="^21$"):
        return self.write(d, f'[[gate]]\nid = "G1"\npurpose = "p"\nkind = "automated"\nrun = \'{self.OK}\'\n'
                             f'pass = "exit 0"\ncontrol = \'{control}\'\ncontrol_expect = \'{expect}\'\n')

    def test_C8_control_that_fails_with_the_gates_finding_is_a_pass(self):
        with tempdir() as d:
            r = run("gates", "run", "--controls", "--file", self.gate(d, self.DETECTS), cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("CONTROL RED", r.stdout)

    def test_C8_control_that_fails_for_another_reason_proves_nothing(self):
        # R-13: any non-zero exit used to count as red, so a crash or an unrelated failure passed.
        with tempdir() as d:
            r = run("gates", "run", "--controls", "--file", self.gate(d, self.BAD), cwd=d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("did not prove", r.stdout)

    def test_C8_validate_requires_a_control_expectation_that_compiles(self):
        with tempdir() as d:
            p = self.write(d, f'[[gate]]\nid = "G1"\npurpose = "p"\nkind = "automated"\nrun = \'{self.OK}\'\n'
                              f'pass = "exit 0"\ncontrol = \'{self.BAD}\'\n')
            r = run("gates", "validate", "--file", p)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("control_expect", r.stdout)
            r = run("gates", "validate", "--file", self.gate(d, self.BAD, expect="(unclosed"))
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("control_expect", r.stdout)

    def test_C8_generated_gates_file_validates(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            repo = d / "repo"
            repo.mkdir()
            cfg = write_config(d, valid_config())
            self.assertEqual(run("apply", repo, "--config", cfg, "--home", d / "home").returncode, 0)
            r = run("gates", "validate", "--file", repo / "gates.toml")
            self.assertEqual(r.returncode, 0, r.stdout)


class SkipIsNotPass(unittest.TestCase):
    """R-6 and R-7: a check that could not run says so, and never reports a pass (U2)."""

    def test_C8_suite_with_skipped_tests_is_not_reported_as_plain_pass(self):
        sys.path.insert(0, str(ROOT / "tests"))
        import run_all
        self.assertEqual(run_all.verdict(0, "Ran 3 tests in 0.1s\n\nOK (skipped=3)\n"), "SKIP (all tests skipped)")
        self.assertEqual(run_all.verdict(0, "Ran 3 tests in 0.1s\n\nOK (skipped=2)\n"), "PASS, 2 of 3 skipped")
        self.assertEqual(run_all.verdict(0, "Ran 3 tests in 0.1s\n\nOK\n"), "PASS")
        self.assertEqual(run_all.verdict(1, "Ran 3 tests in 0.1s\n\nFAILED (failures=1)\n"), "FAIL")

    def test_C13_validation_without_local_copies_skips_with_a_nonzero_exit(self):
        import os
        with tempdir() as d:
            env = dict(os.environ, CHRYSALIS_ROOTS_FILE=str(pathlib.Path(d) / "absent.json"))
            env.pop("CHRYSALIS_SABOTAGE", None)
            r = subprocess.run([sys.executable, str(ROOT / "tests" / "validate_real.py")], env=env,
                               capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("SKIPPED", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


# ------------------------------------------------------------------ C9 register
HEADER = "| ID | State | Defect | Measure | Before | After | Test | Follow-up |\n|---|---|---|---|---|---|---|---|\n"


class Register(unittest.TestCase):
    def check(self, rows, files=()):
        with tempdir() as d:
            d = pathlib.Path(d)
            for f in files:
                (d / f).parent.mkdir(parents=True, exist_ok=True)
                (d / f).write_text("x\n", encoding="utf-8")
            reg = d / "docs" / "register.md"
            reg.parent.mkdir(parents=True, exist_ok=True)
            reg.write_text("# Register\n\n" + HEADER + rows, encoding="utf-8")
            return run("register", "check", "--file", reg, "--root", d)

    def test_C9_complete_closed_row_passes(self):
        r = self.check("| R-1 | CLOSED | crash on empty input | crashes per 100 runs | 100 | 0 | tests/test_empty.py | rule: U4 |\n",
                       files=["tests/test_empty.py"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_C9_closed_row_without_numbers_fails(self):
        r = self.check("| R-1 | CLOSED | crash | crashes | | 0 | tests/t.py | none: trivial |\n", files=["tests/t.py"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("R-1", r.stdout)

    def test_C9_closed_row_with_unmoved_number_fails(self):
        r = self.check("| R-1 | CLOSED | crash | crashes | 5 | 5 | tests/t.py | none: trivial |\n", files=["tests/t.py"])
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_C9_closed_row_needs_an_existing_test(self):
        r = self.check("| R-1 | CLOSED | crash | crashes | 5 | 0 | tests/missing.py | gate: G2 |\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("missing.py", r.stdout)

    def test_C9_follow_up_decision_is_recorded(self):
        r = self.check("| R-1 | CLOSED | crash | crashes | 5 | 0 | tests/t.py | |\n", files=["tests/t.py"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("follow-up", r.stdout.lower())

    def test_C9_open_rows_are_not_held_to_closed_rules(self):
        r = self.check("| R-2 | OPEN | slow | ms | 900 | | | |\n")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_C9_escaped_pipe_and_code_span_pipe_stay_inside_their_cell(self):
        rows = ("| R-1 | CLOSED | split on `a|b` and a \\| c | crashes | 5 | 0 | tests/t.py | rule: U4 |\n"
                "| R-2 | CLOSED | `x|y` | crashes | 5 | 5 | tests/t.py | rule: U4 |\n")
        r = self.check(rows, files=["tests/t.py"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("R-1", r.stdout, "a pipe inside a cell shifted R-1's columns")
        self.assertIn("R-2: CLOSED but the measurement did not move (5)", r.stdout)



# ------------------------------------------------------------------ C1, C11 framework self-check
class SelfCheck(unittest.TestCase):
    def test_C1_framework_check_passes(self):
        r = run("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_C1_rule_without_evidence_fails_the_check(self):
        broken = re.sub(r"(### U3\..*?)\nEvidence:[^\n]*\n", r"\1\n", METHOD_TEXT, count=1, flags=re.S)
        self.assertNotEqual(broken, METHOD_TEXT)
        with tempdir() as d:
            p = pathlib.Path(d) / "METHOD.md"
            p.write_text(broken, encoding="utf-8")
            r = run("check", "--method", p)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("U3", r.stdout)

    def test_C11_template_copying_method_text_fails_the_check(self):
        sentence = sorted(long_sentences(METHOD_TEXT))[0]
        with tempdir() as d:
            t = pathlib.Path(d) / "templates"
            t.mkdir()
            (t / "x.md").write_text(f"Intro.\n\n{sentence}\n", encoding="utf-8")
            r = run("check", "--templates", t)
            self.assertEqual(r.returncode, 1, r.stdout)


# ------------------------------------------------------------------ C14 the in-work project stays unnamed
# Hashes of lower-case name tokens that must never appear in a tracked file: the in-work project, its
# client and its people. Stored as hashes so this test does not commit the names it guards.
UNNAMED = {"2df5a4a7dc5296fa", "d715c79843c99608", "6facd5c71d687fb5", "2504ca8240d180e1",
           "0ba0852ec3860b14", "d2db738e193ec624", "d42e789f1c33e4b5"}


def named_tokens(text: str) -> set:
    import hashlib
    return {t for t in re.findall(r"[a-z0-9]+", text.lower())
            if hashlib.sha256(t.encode()).hexdigest()[:16] in UNNAMED}


class Unnamed(unittest.TestCase):
    def test_C14_no_tracked_file_names_the_in_work_project(self):
        files = git(ROOT, "ls-files").splitlines()
        self.assertGreater(len(files), 50)
        hits = {}
        for rel in files:
            path = ROOT / rel
            if not path.is_file():
                continue
            found = named_tokens(path.read_text(encoding="utf-8", errors="replace"))
            if found:
                hits[rel] = len(found)
        self.assertEqual(hits, {}, "tracked files name the in-work project (counts only, names withheld)")

    def test_C14_the_detector_sees_a_planted_name(self):
        planted = "".join(["sync", "v2"]) + " and " + "".join(["ke", "rv"])
        self.assertEqual(len(named_tokens(planted)), 2)


if __name__ == "__main__":
    unittest.main()
