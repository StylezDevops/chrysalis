"""Spec tests for scripts/chrysalis.py, written from the clauses in .lusser/spec.md before the code.

Every test name carries the clause it proves (test_C4_...). tests/run_all.py --sweep relies on that:
each sabotage injection must make a test for its named clause fail.
"""

import itertools
import json
import pathlib
import random
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import (DELETE, FIXTURES, ROOT, git, make_git_repo, run, tempdir,  # noqa: E402
                     tree_hashes, valid_config, write_config)

REQUIRED = ["project__name", "project__description", "project__problem", "project__users", "stage",
            "repo__existing", "stack__languages", "risk__live_production", "risk__handles_money",
            "risk__handles_personal_data", "risk__auth", "risk__realtime", "risk__client_engagement", "risk__mutates_data",
            "ci__remote", "agents__max_parallel_agents"]


# ------------------------------------------------------------------ C3 validation
class Validation(unittest.TestCase):
    def check(self, cfg):
        with tempdir() as d:
            path = write_config(pathlib.Path(d), cfg)
            return run("validate", "--config", path)

    def test_C3_valid_config_passes(self):
        r = self.check(valid_config())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_C3_bom_prefixed_config_is_read(self):
        # Register row R-5: a config saved by PowerShell 5.1 starts with a byte-order mark.
        with tempdir() as d:
            path = write_config(pathlib.Path(d), valid_config())
            path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
            r = run("validate", "--config", path)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_C3_shipped_example_config_passes(self):
        r = run("validate", "--config", ROOT / "config" / "config_project.example.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_C3_each_missing_required_field_is_a_numbered_question(self):
        for field in REQUIRED:
            with self.subTest(field=field):
                r = self.check(valid_config(**{field: DELETE}))
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertRegex(r.stdout, r"(?m)^Q1\. ")
                self.assertIn(field.replace("__", "."), r.stdout)

    def test_C3_contradictions_are_questions(self):
        cases = {
            "new project marked existing": valid_config(stage="new", repo__existing=True),
            "live stage without live production": valid_config(stage="live"),
            "live production before release": valid_config(risk__live_production=True),
            "agents above 8": valid_config(agents__max_parallel_agents=9),
            "agents below 1": valid_config(agents__max_parallel_agents=0),
            "agents not an integer": valid_config(agents__max_parallel_agents="2"),
            "unknown ci mode": valid_config(ci__remote="sometimes"),
            "unknown field": valid_config(projetc={"name": "typo"}),
            "empty users": valid_config(project__users=[]),
        }
        for name, cfg in cases.items():
            with self.subTest(case=name):
                r = self.check(cfg)
                self.assertEqual(r.returncode, 2, f"{name}: {r.stdout}")
                self.assertRegex(r.stdout, r"(?m)^Q\d+\. ")

    def test_C3_property_random_single_field_damage_never_passes_silently(self):
        rng = random.Random(1125)
        bad_values = [None, "", [], 7, {"x": 1}]
        for _ in range(60):
            field = rng.choice(REQUIRED)
            value = rng.choice(bad_values)
            cfg = valid_config(**{field: value})
            r = self.check(cfg)
            with self.subTest(field=field, value=value):
                if r.returncode == 0:
                    # Only acceptable when the damaged value is still valid for that field.
                    self.assertTrue(field == "agents__max_parallel_agents" and value == 7, r.stdout)
                else:
                    self.assertEqual(r.returncode, 2, r.stdout)

    def test_C3_apply_refuses_while_questions_are_open(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            repo = d / "repo"
            repo.mkdir()
            cfg = write_config(d, valid_config(project__name=DELETE))
            r = run("apply", repo, "--config", cfg, "--home", d / "home")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertEqual(list(repo.iterdir()), [])


# ------------------------------------------------------------------ C2 rule selection
FLAGS = ["live_production", "handles_money", "handles_personal_data", "auth", "realtime",
         "client_engagement", "mutates_data"]


def reference_selection(cfg) -> set:
    """Independent reading of the METHOD.md K table, written by hand from the table text."""
    r, stage = cfg["risk"], cfg["stage"]
    out = set()
    if r["live_production"]:
        out |= {"K1", "K3", "K9"}
    if stage == "pre-release" and not r["live_production"]:
        out.add("K2")
    if r["handles_money"] or r["handles_personal_data"] or r["auth"]:
        out.add("K4")
    if r["realtime"]:
        out.add("K5")
    if "web" in cfg["stack"]["platforms"]:
        out.add("K6")
    if cfg["ci"]["remote"] == "on-request":
        out.add("K7")
    if r["client_engagement"]:
        out.add("K8")
    if r["mutates_data"]:
        out.add("K10")
    return out


class Rules(unittest.TestCase):
    def selected(self, cfg):
        with tempdir() as d:
            path = write_config(pathlib.Path(d), cfg)
            r = run("rules", "--config", path)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return set(re.findall(r"(?m)^([UK]\d+)\b", r.stdout))

    def test_C2_universal_rules_always_selected(self):
        ids = self.selected(valid_config())
        for n in range(1, 17):
            self.assertIn(f"U{n}", ids)

    def test_C2_differential_against_hand_reading_over_all_flag_combinations(self):
        # 64 risk combinations x 2 stages x 2 platform sets x 2 ci modes, filtered to valid configs.
        rng = random.Random(7)
        combos = list(itertools.product([False, True], repeat=len(FLAGS)))
        rng.shuffle(combos)
        checked = 0
        for bits in combos[:24]:
            for stage, platforms, remote in itertools.product(["pre-release", "live"], [["cli"], ["web"]],
                                                               ["on-request", "every-push"]):
                risk = dict(zip(FLAGS, bits))
                if (stage == "live") != risk["live_production"]:
                    continue
                cfg = valid_config(stage=stage, stack__platforms=platforms, ci__remote=remote)
                cfg["risk"] = risk
                got = {i for i in self.selected(cfg) if i.startswith("K")}
                self.assertEqual(got, reference_selection(cfg), json.dumps(cfg["risk"]) + stage)
                checked += 1
        self.assertGreater(checked, 40)

    def test_C2_every_conditional_rule_has_a_parsable_condition(self):
        r = run("rules", "--list-conditions")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ids = re.findall(r"(?m)^(K\d+)\s", r.stdout)
        self.assertEqual(ids, [f"K{n}" for n in range(1, 11)])

    def test_C2_a_flag_that_is_not_a_bool_is_refused_not_read_as_true(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import chrysalis
        cond = chrysalis.Condition("risk.auth")
        self.assertTrue(cond.evaluate({"risk": {"auth": True}}))
        self.assertFalse(cond.evaluate({"risk": {"auth": False}}))
        self.assertFalse(cond.evaluate({"risk": {}}))
        for bad in ("false", 0, [], "yes"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                cond.evaluate({"risk": {"auth": bad}})


# ------------------------------------------------------------------ C4, C5, C6 existing repo
EXISTING = {
    "CLAUDE.md": "# Existing contract\nDo the thing.\n",
    "README.md": "# Existing\n",
    "src/app.py": "print('hello')\n",
    ".lusser/spec.md": "# Spec\n\n- C1. Something.\n",
    "decisions/ADR-001-first.md": "# ADR-001\n",
    "docs/AUDIT_REGISTER.md": "| ID | State |\n",
    ".claude/settings.json": "{}\n",
    ".claude/hooks/guard.py": "print('guard')\n",
    "tools/ci_local.bat": "@echo off\n",
}


class ExistingRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)
        self.repo = make_git_repo(self.base / "repo", EXISTING)
        git(self.repo, "branch", "feature/x")
        self.cfg = write_config(self.base, valid_config(repo__existing=True))
        self.home = self.base / "home"

    def tearDown(self):
        self._tmp.cleanup()

    def apply(self):
        return run("apply", self.repo, "--config", self.cfg, "--home", self.home)

    def test_C4_no_pre_existing_file_changes(self):
        before = tree_hashes(self.repo)
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = tree_hashes(self.repo)
        for path, digest in before.items():
            self.assertIn(path, after, f"deleted: {path}")
            self.assertEqual(after[path], digest, f"changed: {path}")

    def test_C4_existing_claude_md_becomes_a_proposal(self):
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        proposals = list((self.repo / ".chrysalis").rglob("proposals/CLAUDE.md"))
        self.assertEqual(len(proposals), 1, r.stdout)
        self.assertIn("PROPOSE CLAUDE.md", r.stdout)

    def test_C4_second_run_changes_nothing_written_by_the_first(self):
        self.assertEqual(self.apply().returncode, 0)
        before = tree_hashes(self.repo)
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = tree_hashes(self.repo)
        for path, digest in before.items():
            self.assertEqual(after.get(path), digest, f"changed on second run: {path}")

    def test_C5_no_commit_branch_remote_or_history_change(self):
        state = lambda: (git(self.repo, "rev-parse", "HEAD"), git(self.repo, "branch", "--list"),  # noqa: E731
                         git(self.repo, "remote", "-v"), git(self.repo, "stash", "list"),
                         git(self.repo, "rev-list", "--all", "--count"))
        before = state()
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(state(), before)

    def test_C5_staging_area_untouched(self):
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "")

    def test_C6_inventory_lists_existing_assets(self):
        r = run("inspect", self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        inv = json.loads(r.stdout)
        found = json.dumps(inv)
        for needle in ["CLAUDE.md", ".claude/settings.json", ".claude/hooks/guard.py", ".lusser",
                       "decisions", "docs/AUDIT_REGISTER.md", "tools/ci_local.bat", "feature/x"]:
            self.assertIn(needle, found, needle)

    def test_C6_folders_past_the_depth_limit_are_reported_and_reachable(self):
        deep = self.repo / "services" / "api" / "v1" / "docs"
        deep.mkdir(parents=True)
        (deep / "REGISTER.md").write_text("# R\n", encoding="utf-8")
        shallow = json.loads(run("inspect", self.repo).stdout)
        self.assertIn("services/api/v1/docs", shallow["dirs_not_walked"])
        self.assertNotIn("services/api/v1/docs/REGISTER.md", shallow["assets"].get("register", []))
        deep_inv = json.loads(run("inspect", self.repo, "--max-depth", "6").stdout)
        self.assertEqual(deep_inv["dirs_not_walked"], [])
        self.assertIn("services/api/v1/docs/REGISTER.md", deep_inv["assets"].get("register", []))
        r = run("plan", self.repo, "--config", self.cfg, "--home", self.home)
        self.assertIn("not searched", r.stdout)

    def test_C4_no_home_writes_nothing_outside_the_repo(self):
        r = run("apply", self.repo, "--config", self.cfg, "--home", self.home, "--no-home")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.home.exists(), "apply wrote to the home folder despite --no-home")

    def test_C4_plan_names_the_home_write_before_apply_makes_it(self):
        r = run("plan", self.repo, "--config", self.cfg, "--home", self.home)
        self.assertIn("engineering-guardrails.md (outside the repo", r.stdout)
        self.assertFalse(self.home.exists(), "plan wrote to the home folder")

    def test_C6_register_loop_config_is_not_a_register(self):
        # Register row R-1: found on the CHRYSOS copy, where case-insensitive matching took
        # .claude/register-loop.md for a defect register.
        r = run("inspect", self.repo)
        inv = json.loads(r.stdout)
        self.assertNotIn(".claude/register-loop.md", inv["assets"].get("register", []))
        (self.repo / ".claude" / "register-loop.md").write_text("config\n", encoding="utf-8")
        inv = json.loads(run("inspect", self.repo).stdout)
        self.assertEqual(inv["assets"]["register"], ["docs/AUDIT_REGISTER.md"])

    def test_C6_existing_file_under_another_case_is_reused(self):
        # Register row R-2: CHRYSOS has docs/BACKLOG.md; apply proposed a second backlog.
        (self.repo / "docs" / "BACKLOG.md").write_text("# Backlog\n", encoding="utf-8")
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout, r"(?m)^REUSE docs/backlog.md -> docs/BACKLOG.md")
        self.assertNotRegex(r.stdout, r"(?m)^PROPOSE docs/backlog.md")

    def test_C6_existing_lusser_files_are_reused_not_proposed(self):
        # Register row R-3: an existing .lusser/ got template proposals for its live files.
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout, r"(?m)^REUSE \.lusser/spec\.md")
        self.assertNotRegex(r.stdout, r"(?m)^PROPOSE \.lusser/")

    def test_C6_equivalents_are_reused_not_duplicated(self):
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse((self.repo / "docs" / "adr").exists(), "ADR folder duplicated beside decisions/")
        self.assertFalse((self.repo / "docs" / "register.md").exists(), "register duplicated")
        self.assertFalse((self.repo / "gates.toml").exists(), "gate list duplicated beside ci_local")
        self.assertRegex(r.stdout, r"REUSE .*decisions")
        self.assertRegex(r.stdout, r"REUSE .*AUDIT_REGISTER")


# ------------------------------------------------------------------ C7, C11 new project
METHOD_TEXT = (ROOT / "METHOD.md").read_text(encoding="utf-8")


def long_sentences(text, min_words=8):
    body = re.sub(r"`[^`]*`", "", text)
    parts = re.split(r"(?<=[.!?])\s+|\n", body)
    return {re.sub(r"\s+", " ", s).strip(" -*|") for s in parts if len(s.split()) >= min_words}


class NewProject(unittest.TestCase):
    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)
        self.repo = self.base / "new"
        self.repo.mkdir()
        cfg = valid_config(stage="pre-release", stack__platforms=["web"], risk__handles_money=True)
        self.cfg = write_config(self.base, cfg)
        self.r = run("apply", self.repo, "--config", self.cfg, "--home", self.base / "home")

    def tearDown(self):
        self._tmp.cleanup()

    def test_C7_core_files_created(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        for rel in ["CLAUDE.md", "initial.md", "docs/backlog.md", "gates.toml", ".lusser/spec.md",
                    "docs/register.md", "docs/handover.md", "docs/adr/ADR-000-template.md",
                    "docs/standards/ready-and-done.md", "docs/standards/threat-model.md"]:
            self.assertTrue((self.repo / rel).is_file(), rel)

    def test_C7_initial_md_carries_the_config(self):
        text = (self.repo / "initial.md").read_text(encoding="utf-8")
        for needle in ["Sample tool", "A command-line tool used by the Chrysalis tests.", "the test suite",
                       "python"]:
            self.assertIn(needle, text)
        self.assertNotIn("{{", text)

    def test_C7_conditional_files_follow_the_rules(self):
        self.assertTrue((self.repo / "docs/standards/threat-model.md").exists())  # K4 holds
        self.assertFalse((self.repo / "docs/standards/change-request.md").exists())  # K1 does not

    def test_C11_claude_md_cites_rule_ids_without_copying_text(self):
        text = (self.repo / "CLAUDE.md").read_text(encoding="utf-8")
        for rid in ["U1", "U10", "U16", "K2", "K4", "K6", "K7"]:
            self.assertRegex(text, rf"\b{rid}\b")
        self.assertNotRegex(text, r"\bK1\b")
        copied = long_sentences(METHOD_TEXT) & long_sentences(text)
        self.assertEqual(copied, set(), copied)

    def test_C11_no_generated_file_copies_method_text(self):
        method = long_sentences(METHOD_TEXT)
        for f in self.repo.rglob("*"):
            if f.is_file() and ".chrysalis" not in f.parts:
                copied = method & long_sentences(f.read_text(encoding="utf-8"))
                self.assertEqual(copied, set(), f"{f.name}: {copied}")

    def test_C7_guardrails_installed_when_absent(self):
        self.assertTrue((self.base / "home" / ".claude" / "engineering-guardrails.md").is_file())


class Guardrails(unittest.TestCase):
    def test_C4_existing_guardrails_never_overwritten(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            home = d / "home" / ".claude"
            home.mkdir(parents=True)
            (home / "engineering-guardrails.md").write_text("mine\n", encoding="utf-8")
            repo = d / "repo"
            repo.mkdir()
            cfg = write_config(d, valid_config())
            r = run("apply", repo, "--config", cfg, "--home", d / "home")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((home / "engineering-guardrails.md").read_text(encoding="utf-8"), "mine\n")


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
            p = self.write(d, f'[[gate]]\nid = "G1"\npurpose = "p"\nkind = "automated"\nrun = \'{self.OK}\'\n'
                              f'pass = "exit 0"\ncontrol = \'{self.OK}\'\n')
            r = run("gates", "run", "--controls", "--file", p, cwd=d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("control did not fail", r.stdout)

    def test_C8_control_that_fails_is_a_pass(self):
        with tempdir() as d:
            p = self.write(d, f'[[gate]]\nid = "G1"\npurpose = "p"\nkind = "automated"\nrun = \'{self.OK}\'\n'
                              f'pass = "exit 0"\ncontrol = \'{self.BAD}\'\n')
            r = run("gates", "run", "--controls", "--file", p, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout)

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
        import subprocess
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


# ------------------------------------------------------------------ C12 worktree procedure
class Worktrees(unittest.TestCase):
    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)
        self.repo = make_git_repo(self.base / "repo", {"a.txt": "a\n"})
        self.wt_root = self.base / "wts"

    def tearDown(self):
        self._tmp.cleanup()

    def wt(self, *args):
        return run("worktree", *args, "--repo", self.repo, "--root", self.wt_root)

    def commit_in(self, path, name):
        (path / name).write_text("x\n", encoding="utf-8")
        git(path, "add", name)
        git(path, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", name)

    def test_C12_new_reports_the_current_base(self):
        head = git(self.repo, "rev-parse", "--short", "HEAD")
        r = self.wt("new", "job1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(head, r.stdout)
        self.assertTrue((self.wt_root / "job1" / "a.txt").exists())

    def use_trunk(self, config_text):
        git(self.repo, "branch", "-m", "main", "trunk")
        if config_text is not None:
            (self.repo / "config_project.json").write_text(config_text, encoding="utf-8")

    def test_C12_base_defaults_to_the_configured_default_branch(self):
        self.use_trunk('{"repo": {"default_branch": "trunk"}}')
        r = self.wt("new", "job-trunk")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("trunk", r.stdout)
        self.assertIn("config_project.json", r.stdout, "the output does not say where the base came from")

    def test_C12_explicit_base_overrides_the_config(self):
        self.use_trunk('{"repo": {"default_branch": "nowhere"}}')
        r = run("worktree", "new", "job-x", "--repo", self.repo, "--root", self.wt_root, "--base", "trunk")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_C12_unreadable_config_fails_closed(self):
        self.use_trunk("{not json")
        r = self.wt("new", "job-bad")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("config_project.json", r.stdout)
        self.assertFalse((self.wt_root / "job-bad").exists())

    def test_C12_sweep_uses_the_configured_base(self):
        self.use_trunk('{"repo": {"default_branch": "trunk"}}')
        self.assertEqual(self.wt("new", "job-sw").returncode, 0)
        r = run("worktree", "sweep", "--repo", self.repo, "--apply")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("agent/job-sw", git(self.repo, "branch", "--list"))

    def test_C12_finish_refuses_an_unmerged_branch(self):
        self.assertEqual(self.wt("new", "job2").returncode, 0)
        self.commit_in(self.wt_root / "job2", "b.txt")
        r = self.wt("finish", "job2")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue((self.wt_root / "job2").exists(), "unmerged work was removed")
        self.assertIn("agent/job2", git(self.repo, "branch", "--list"))

    def test_C12_finish_refuses_a_dirty_worktree(self):
        self.assertEqual(self.wt("new", "job3").returncode, 0)
        (self.wt_root / "job3" / "scratch.txt").write_text("unsaved\n", encoding="utf-8")
        r = self.wt("finish", "job3")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue((self.wt_root / "job3" / "scratch.txt").exists())

    def test_C12_finish_cleans_up_after_merge(self):
        self.assertEqual(self.wt("new", "job4").returncode, 0)
        self.commit_in(self.wt_root / "job4", "c.txt")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "merge", "-q", "--no-ff",
            "-m", "merge job4", "agent/job4")
        r = self.wt("finish", "job4")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse((self.wt_root / "job4").exists())
        self.assertNotIn("agent/job4", git(self.repo, "branch", "--list"))
        self.assertEqual(git(self.repo, "worktree", "list").count("\n"), 0)

    def merge(self, branch):
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "merge", "-q", "--no-ff",
            "-m", f"merge {branch}", branch)

    def test_C12_finish_removes_the_build_directory(self):
        self.assertEqual(self.wt("new", "job5").returncode, 0)
        self.commit_in(self.wt_root / "job5", "d.txt")
        self.merge("agent/job5")
        build = self.base / "build-job5"
        (build / "obj").mkdir(parents=True)
        (build / "obj" / "x.o").write_text("o\n", encoding="utf-8")
        r = self.wt("finish", "job5", "--build-dir", build)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(build.exists(), "build directory left behind")

    def test_C12_finish_refuses_a_build_dir_that_holds_the_repo(self):
        self.assertEqual(self.wt("new", "job6").returncode, 0)
        r = self.wt("finish", "job6", "--build-dir", self.base)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue((self.repo / "a.txt").exists())
        self.assertTrue((self.wt_root / "job6").exists())

    def test_C12_sweep_removes_merged_agent_leftovers_and_keeps_the_rest(self):
        # merged, with a worktree (this tool's naming)
        self.assertEqual(self.wt("new", "done").returncode, 0)
        self.commit_in(self.wt_root / "done", "e.txt")
        self.merge("agent/done")
        # merged, branch only (Claude Code's naming), pointing at a commit already on main
        git(self.repo, "branch", "worktree-agent-abc123")
        # unmerged agent work, and a merged branch that is not an agent's
        self.assertEqual(self.wt("new", "open").returncode, 0)
        self.commit_in(self.wt_root / "open", "f.txt")
        git(self.repo, "branch", "feature/keep")

        dry = run("worktree", "sweep", "--repo", self.repo)
        self.assertEqual(dry.returncode, 0, dry.stdout)
        self.assertIn("worktree-agent-abc123", git(self.repo, "branch", "--list"), "dry run removed a branch")
        self.assertTrue((self.wt_root / "done").exists(), "dry run removed a worktree")

        r = run("worktree", "sweep", "--apply", "--repo", self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        branches = git(self.repo, "branch", "--list")
        self.assertNotIn("agent/done", branches)
        self.assertNotIn("worktree-agent-abc123", branches)
        self.assertFalse((self.wt_root / "done").exists())
        self.assertIn("agent/open", branches, "unmerged agent work was removed")
        self.assertTrue((self.wt_root / "open" / "f.txt").exists())
        self.assertIn("feature/keep", branches, "a non-agent branch was removed")


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
