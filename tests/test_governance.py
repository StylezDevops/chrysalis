"""Spec tests for clauses C15 to C18: proportion, fault states, compliance and portability.

Each test drives chrysalis.py as a user would, on a temporary git repository, and reads its exit code
and output. Markers are assembled from pieces so the deferral hook does not refuse this file.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT, git, make_git_repo, run, tempdir, tree_hashes, valid_config, write_config  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import common  # noqa: E402
import project_config  # noqa: E402
import rules  # noqa: E402
import proportion  # noqa: E402

MK = "TO" + "DO"
HEADER = "| ID | State | Defect | Measure | Before | After | Test | Follow-up |\n|---|---|---|---|---|---|---|---|\n"
GOOD_SPEC = """# Spec: t

Budget: 3 parts

## Clauses

- C1. The tool prints a greeting.

## Ambiguities

- A1. Q: Which greeting?
      Resolution: Hello. (human, 2026-11-28)
"""
GOOD_PARTS = "| # | Part | Kind | Justification | Proven |\n|---|---|---|---|---|\n| 1 | app.py | module | entry point | no |\n"
GOOD_CHECKS = '[[check]]\nclause = "C1"\nkind = "spec-test"\nref = "tests/test_app.py"\n'


def commit_all(repo, message="change"):
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", message)


# ------------------------------------------------------------------ C15 proportion
class Grades(unittest.TestCase):
    def test_C15_every_universal_rule_is_graded_once(self):
        universal, _ = rules.parse_method(common.METHOD.read_text(encoding="utf-8"))
        g = rules.grades()
        self.assertEqual(sorted(g, key=lambda r: int(r[1:])), [r for r, _ in universal])
        self.assertEqual(proportion.grade_problems(g, [r for r, _ in universal]), [])

    def test_C15_check_fails_on_an_ungraded_rule(self):
        text = common.PROPORTION.read_text(encoding="utf-8")
        broken = re.sub(r"(?m)^\| U12 \|.*\n", "", text)
        self.assertNotEqual(broken, text)
        with tempdir() as d:
            f = pathlib.Path(d) / "PROPORTION.md"
            f.write_text(broken, encoding="utf-8")
            r = run("check", "--proportion", f)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("U12: no row", r.stdout)

    def test_C15_check_fails_on_an_agent_file_over_the_size_limit(self):
        with tempdir() as d:
            f = pathlib.Path(d) / "METHOD.md"
            f.write_text(common.METHOD.read_text(encoding="utf-8") + "x" * common.AGENT_FILE_LIMIT,
                         encoding="utf-8")
            r = run("check", "--method", f)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("U9", r.stdout)

    def test_C15_check_fails_on_a_source_file_over_the_line_limit(self):
        with tempdir() as d:
            src = pathlib.Path(d) / "big"
            src.mkdir()
            (src / "small.py").write_text("x = 1\n" * 500, encoding="utf-8")
            (src / "large.py").write_text("x = 1\n" * 501, encoding="utf-8")
            r = run("check", "--sources", src)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("big/large.py is 501 lines", r.stdout)
        self.assertNotIn("small.py", r.stdout)

    def test_C15_property_overhead_scales_with_class(self):
        g = rules.grades()
        counts = [len(proportion.obligations(g, c)[0]) for c in proportion.CLASSES]
        self.assertLess(counts[0], counts[1], counts)
        self.assertLessEqual(counts[1], counts[2], counts)
        asked = [{rid for rid, _ in proportion.obligations(g, c)[0]} for c in proportion.CLASSES]
        self.assertLessEqual(asked[0], asked[1], "C1 drops a rule C0 asks for")
        self.assertLessEqual(asked[1], asked[2], "C2 drops a rule C1 asks for")


class Classify(unittest.TestCase):
    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)
        self.repo = make_git_repo(self.base / "repo", {"app.py": "x = 1\n", "README.md": "# app\n",
                                                        "core/money.py": "rate = 1\n"})

    def tearDown(self):
        self._tmp.cleanup()

    def config(self, **overrides):
        cfg = valid_config(**overrides)
        (self.repo / "config_project.json").write_text(json.dumps(cfg), encoding="utf-8")
        commit_all(self.repo, "config")
        git(self.repo, "branch", "-f", "main", "HEAD")

    def classify(self, *extra):
        return run("classify", "--repo", self.repo, *extra)

    def cls(self, r):
        m = re.search(r"(?m)^class: (C\d)", r.stdout)
        self.assertIsNotNone(m, r.stdout + r.stderr)
        return m.group(1)

    def test_C15_docs_only_change_is_c0_and_asks_for_little(self):
        (self.repo / "README.md").write_text("# app\n\n" + "More words.\n" * 200, encoding="utf-8")
        r = self.classify()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.cls(r), "C0")
        self.assertIn("docs only", r.stdout)
        self.assertNotIn("lusser spec", r.stdout.split("C0 asks for:")[1].split("controls")[0])

    def test_C15_small_code_change_is_c0(self):
        (self.repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        self.assertEqual(self.cls(self.classify()), "C0")

    def test_C15_new_file_or_many_lines_is_c1(self):
        (self.repo / "extra.py").write_text("y = 1\n", encoding="utf-8")
        self.assertEqual(self.cls(self.classify()), "C1")
        (self.repo / "extra.py").unlink()
        (self.repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(30)), encoding="utf-8")
        r = self.classify()
        self.assertEqual(self.cls(r), "C1")
        self.assertIn("change.small_lines", r.stdout)

    def test_C15_critical_path_manifest_and_machinery_are_c2(self):
        self.config(change={"critical_paths": ["core/*"]})
        cases = {"core/money.py": "rate = 2\n", "requirements.txt": "requests\n", "gates.toml": "x = 1\n"}
        for path, text in cases.items():
            with self.subTest(path=path):
                f = self.repo / path
                old = f.read_text(encoding="utf-8") if f.exists() else None
                f.write_text(text, encoding="utf-8")
                self.assertEqual(self.cls(self.classify()), "C2", path)
                if old is None:
                    f.unlink()
                else:
                    f.write_text(old, encoding="utf-8")

    def test_C15_live_production_allows_c0_only_for_docs(self):
        self.config(stage="live", risk__live_production=True)
        (self.repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        r = self.classify()
        self.assertEqual(self.cls(r), "C1")
        self.assertIn("risk.live_production", r.stdout)

    def test_C15_a_declared_class_is_never_lowered(self):
        (self.repo / "extra.py").write_text("y = 1\n", encoding="utf-8")
        low = self.classify("--declared", "C0")
        self.assertEqual(low.returncode, 1, low.stdout)
        self.assertIn("never lowered", low.stdout)
        high = self.classify("--declared", "C2")
        self.assertEqual(high.returncode, 0, high.stdout)

    def test_C15_a_sensitive_risk_flag_needs_its_critical_paths(self):
        # R-18: risk.auth could be true while a small change to auth code classified as C0, because
        # nothing tied the risk flags to change.critical_paths.
        for flag in ("auth", "handles_money", "handles_personal_data", "mutates_data"):
            with self.subTest(flag=flag):
                qs = project_config.questions(valid_config(**{f"risk__{flag}": True}))
                self.assertTrue(any("change.critical_paths" in q and flag in q for q in qs), qs)
                ok = valid_config(**{f"risk__{flag}": True}, change={"critical_paths": ["core/*"]})
                self.assertEqual(project_config.questions(ok), [])

    def test_C15_a_small_change_to_a_sensitive_path_is_c2(self):
        self.config(risk__auth=True, change={"critical_paths": ["core/*"]})
        (self.repo / "core" / "money.py").write_text("rate = 3\n", encoding="utf-8")
        self.assertEqual(self.cls(self.classify()), "C2")

    def test_C15_an_invalid_config_stops_classify(self):
        (self.repo / "config_project.json").write_text('{"stage": "sideways"}', encoding="utf-8")
        r = self.classify()
        self.assertEqual(r.returncode, 2, r.stdout)


class Adapt(unittest.TestCase):
    ENTRY = {"rule": "U12", "change": "a handover only when work is left open", "reason": "pilot data",
             "decided": "A. Lead (human, 2026-11-28)", "revisit": "2999-01-01"}

    def questions(self, *entries):
        return project_config.questions(valid_config(adapt=list(entries)))

    def test_C15_a_practice_can_be_adapted_by_a_human(self):
        self.assertEqual(self.questions(self.ENTRY), [])

    def test_C15_a_control_cannot_be_adapted(self):
        qs = self.questions(dict(self.ENTRY, rule="U2"))
        self.assertTrue(any("control" in q for q in qs), qs)

    def test_C15_an_adaptation_needs_a_human_decision_and_known_fields(self):
        self.assertTrue(any("human" in q for q in self.questions(dict(self.ENTRY, decided="the agent"))))
        self.assertTrue(any("unknown field" in q for q in self.questions(dict(self.ENTRY, expires="never"))))
        self.assertTrue(any("no 'revisit'" in q for q in self.questions(
            {k: v for k, v in self.ENTRY.items() if k != "revisit"})))

    def test_C15_the_contract_shows_the_adaptation(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            repo = d / "new"
            repo.mkdir()
            cfg = write_config(d, valid_config(adapt=[self.ENTRY]))
            r = run("apply", repo, "--config", cfg, "--no-home")
            self.assertEqual(r.returncode, 0, r.stdout)
            text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^- U12: .*\(adapted: a handover only when work is left open")


# ------------------------------------------------------------------ C16 fault states
class FaultStates(unittest.TestCase):
    def check(self, rows, *extra):
        with tempdir() as d:
            d = pathlib.Path(d)
            reg = d / "docs" / "register.md"
            reg.parent.mkdir(parents=True)
            reg.write_text("# Register\n\n" + HEADER + rows, encoding="utf-8")
            return run("register", "check", "--file", reg, "--root", d, *extra)

    def test_C16_scheduled_needs_owner_due_date_and_reason(self):
        ok = self.check("| R-1 | SCHEDULED | slow export | ms | 900 | | | scheduled: A. Dev, due 2999-01-01, "
                        "no user reaches the export before launch |\n")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        bad = self.check("| R-1 | SCHEDULED | slow export | ms | 900 | | | later |\n")
        self.assertEqual(bad.returncode, 1, bad.stdout)

    def test_C16_accepted_needs_a_human_decision_and_revisit_date(self):
        ok = self.check("| R-1 | ACCEPTED | rounding | pence | 1 | | | accepted: A. Owner (human, 2026-11-28), "
                        "revisit 2999-01-01, within the tolerance finance agreed |\n")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        agent = self.check("| R-1 | ACCEPTED | rounding | pence | 1 | | | accepted: the agent, revisit "
                           "2999-01-01, seems fine |\n")
        self.assertEqual(agent.returncode, 1, agent.stdout)
        self.assertIn("only a human", agent.stdout)

    def test_C16_a_passed_due_or_revisit_date_fails(self):
        for row in ("| R-1 | SCHEDULED | x | y | 1 | | | scheduled: A. Dev, due 2000-01-01, reason |\n",
                    "| R-1 | ACCEPTED | x | y | 1 | | | accepted: A (human, 1999-12-01), revisit 2000-01-01, reason |\n"):
            with self.subTest(row=row[:30]):
                r = self.check(row)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("has passed", r.stdout)

    def test_C16_unknown_state_fails(self):
        r = self.check("| R-1 | WONTFIX | x | y | 1 | | | none: meh |\n")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_C16_open_blocks_only_a_release(self):
        row = "| R-1 | OPEN | crash | crashes | 3 | | | |\n"
        self.assertEqual(self.check(row).returncode, 0)
        r = self.check(row, "--release")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("blocks a release", r.stdout)


# ------------------------------------------------------------------ C17 doctor and CI
class Doctor(unittest.TestCase):
    """A project set up by apply, with its spec filled in, passes doctor; each kind of drift fails."""

    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)
        self.repo = self.base / "proj"
        self.repo.mkdir()
        self.cfg = valid_config(repo__existing=True)
        (self.repo / "config_project.json").write_text(json.dumps(self.cfg, indent=2), encoding="utf-8")
        r = run("apply", self.repo, "--no-home")
        self.assertEqual(r.returncode, 0, r.stdout)
        shutil.rmtree(self.repo / ".chrysalis")
        lus = self.repo / ".lusser"
        (lus / "spec.md").write_text(GOOD_SPEC, encoding="utf-8")
        (lus / "parts.md").write_text(GOOD_PARTS, encoding="utf-8")
        (lus / "checks.toml").write_text(GOOD_CHECKS, encoding="utf-8")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_app.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
        reg = self.repo / "docs" / "register.md"
        reg.write_text(reg.read_text(encoding="utf-8").replace(
            "|---|---|---|---|---|---|---|---|\n",
            "|---|---|---|---|---|---|---|---|\n| R-1 | OPEN | slow start | ms | 900 | | | |\n"
            "| R-2 | CLOSED | crash | crashes | 3 | 0 | tests/test_app.py | none: covered by the test |\n"),
            encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        commit_all(self.repo, "set up")

    def tearDown(self):
        self._tmp.cleanup()

    def doctor(self, *extra):
        return run("doctor", "--repo", self.repo, *extra)

    def failing(self, r):
        return re.findall(r"(?m)^FAIL  (.+)$", r.stdout)

    def test_C17_a_project_on_the_method_passes_and_doctor_writes_nothing(self):
        before = tree_hashes(self.repo)
        r = self.doctor()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(tree_hashes(self.repo), before, "doctor changed a file")

    def test_C17_an_uncited_marker_fails(self):
        (self.repo / "app.py").write_text(f"print('hello')  # {MK} tidy\n", encoding="utf-8")
        commit_all(self.repo)
        r = self.doctor()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("deferral markers", self.failing(r))

    def test_C17_a_citation_must_point_at_a_live_row(self):
        for cited, ok in (("R-1", True), ("R-2", False), ("R-9", False)):
            with self.subTest(cited=cited):
                (self.repo / "app.py").write_text(f"print('hello')  # {MK}({cited}) tidy\n", encoding="utf-8")
                commit_all(self.repo)
                r = self.doctor()
                self.assertEqual(r.returncode == 0, ok, r.stdout)

    def test_C17_an_exempt_file_is_counted_not_hidden(self):
        (self.repo / "app.py").write_text(f"WORDS = ['{MK}']\n", encoding="utf-8")
        cfg = dict(self.cfg, markers={"exempt": ["app.py"]})
        (self.repo / "config_project.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        commit_all(self.repo)
        r = self.doctor()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 file(s) exempt by markers.exempt", r.stdout)

    def test_C17_the_contract_must_match_the_config(self):
        cfg = dict(self.cfg, risk=dict(self.cfg["risk"], handles_money=True), change={"critical_paths": ["app.py"]})
        (self.repo / "config_project.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        r = self.doctor()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("does not list K4", r.stdout)

    def test_C17_a_critical_path_that_matches_nothing_fails(self):
        # R-18: a critical-path list that no longer matches the code protects nothing.
        cfg = dict(self.cfg, change={"critical_paths": ["app.py", "src/auth/*"]})
        (self.repo / "config_project.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        commit_all(self.repo)
        r = self.doctor()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("src/auth/* matches no tracked file", r.stdout)
        self.assertNotIn("'app.py' matches", r.stdout)

    def test_C17_an_overdue_adaptation_fails(self):
        entry = dict(Adapt.ENTRY, revisit="2000-01-01")
        cfg = dict(self.cfg, adapt=[entry])
        (self.repo / "config_project.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        r = self.doctor()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("due for revisit", r.stdout)

    def test_C17_release_mode_fails_on_an_open_row(self):
        r = self.doctor("--release")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("register", self.failing(r))

    def test_C17_missing_pieces_each_fail(self):
        for rel in ("docs/handover.md", "gates.toml", "AGENTS.md"):
            with self.subTest(missing=rel):
                f = self.repo / rel
                saved = f.read_bytes()
                f.unlink()
                try:
                    self.assertEqual(self.doctor().returncode, 1, rel)
                finally:
                    f.write_bytes(saved)

    def test_C17_apply_proposes_a_ci_workflow_pinned_to_a_framework_commit(self):
        text = (self.repo / ".github" / "workflows" / "chrysalis.yml").read_text(encoding="utf-8")
        self.assertIn("chrysalis.py\" doctor --repo .", text)
        self.assertIn('--base "origin/${{ github.base_ref }}"', text)
        ref = re.search(r"(?m)^\s*ref: (\S+)$", text).group(1)
        expected = git(ROOT, "rev-parse", "HEAD")
        self.assertEqual(ref, expected)

    def test_C17_proportion_says_what_enforces_each_rule(self):
        for rid, g in rules.grades().items():
            with self.subTest(rule=rid):
                self.assertTrue(g["enforced"].strip(), rid)


# ------------------------------------------------------------------ C18 portability
class Portability(unittest.TestCase):
    def test_C18_existing_agents_md_is_proposed_not_overwritten(self):
        with tempdir() as d:
            d = pathlib.Path(d)
            repo = make_git_repo(d / "repo", {"AGENTS.md": "# Ours\n"})
            cfg = write_config(d, valid_config(repo__existing=True))
            r = run("apply", repo, "--config", cfg, "--no-home")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("PROPOSE AGENTS.md", r.stdout)
            self.assertEqual((repo / "AGENTS.md").read_text(encoding="utf-8"), "# Ours\n")

    def test_C18_pre_commit_manifest_points_at_an_executable_hook(self):
        text = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        entry = re.search(r"(?m)^\s*entry:\s*(\S+)", text).group(1)
        self.assertRegex(text, r"(?m)^\s*language:\s*script$")
        self.assertTrue((ROOT / entry).read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        mode = git(ROOT, "ls-files", "-s", entry).split()[0]
        self.assertEqual(mode, "100755", "pre-commit runs a script entry only if git marks it executable")

    def test_C18_every_documented_subcommand_exists(self):
        help_text = run("--help").stdout
        known = set(re.search(r"\{([^}]*)\}", help_text).group(1).split(","))
        for doc in ("README.md", "docs/pilot.md", "PROPORTION.md", "templates/AGENTS.md"):
            text = (ROOT / doc).read_text(encoding="utf-8")
            for sub in set(re.findall(r"chrysalis\.py\"? (\w+)", text)):
                with self.subTest(doc=doc, sub=sub):
                    self.assertIn(sub, known, f"{doc} names chrysalis.py {sub}, which does not exist")


class SkillsInstall(unittest.TestCase):
    def setUp(self):
        self._tmp = tempdir()
        self.dest = pathlib.Path(self._tmp.name) / "skills"

    def tearDown(self):
        self._tmp.cleanup()

    def install(self, *extra):
        return run("skills", "install", "--dest", self.dest, *extra)

    def test_C18_dry_run_writes_nothing(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(self.dest.exists())

    def test_C18_install_then_reinstall_is_identical(self):
        self.assertEqual(self.install("--apply").returncode, 0)
        self.assertTrue((self.dest / "lusser" / "SKILL.md").is_file())
        again = self.install("--apply")
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertNotIn("INSTALL ", again.stdout)
        self.assertIn("SKIP     lusser (identical)", again.stdout)

    def test_C18_a_different_skill_of_the_same_name_is_never_overwritten(self):
        mine = self.dest / "lusser" / "SKILL.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("---\nname: lusser\n---\nmy own skill\n", encoding="utf-8")
        r = self.install("--apply")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("CONFLICT lusser", r.stdout)
        self.assertEqual(mine.read_text(encoding="utf-8"), "---\nname: lusser\n---\nmy own skill\n")

    def test_C18_prefix_installs_beside_and_renames_the_skill(self):
        mine = self.dest / "lusser" / "SKILL.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("mine\n", encoding="utf-8")
        r = self.install("--apply", "--prefix", "chrysalis-")
        self.assertEqual(r.returncode, 0, r.stdout)
        installed = (self.dest / "chrysalis-lusser" / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(installed, r"(?m)^name: chrysalis-lusser$")
        self.assertEqual(mine.read_text(encoding="utf-8"), "mine\n")


if __name__ == "__main__":
    unittest.main()
