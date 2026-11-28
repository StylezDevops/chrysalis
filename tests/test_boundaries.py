"""The framework's own adversarial boundaries: malformed input, hostile file names and paths, symlink
loops, deep trees, enormous output, and Windows paths. Every command must fail with a message, never a
traceback, and never act outside the repository it was pointed at.
"""

import json
import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT, make_git_repo, run, tempdir, valid_config, write_config  # noqa: E402

HEADER = "| ID | State | Defect | Measure | Before | After | Test | Follow-up |\n|---|---|---|---|---|---|---|---|\n"


def no_traceback(test, r):
    test.assertNotIn("Traceback", r.stdout + r.stderr, r.stdout + r.stderr)


class MalformedInput(unittest.TestCase):
    def test_C3_malformed_json_config_is_refused_with_a_message(self):
        with tempdir() as d:
            p = pathlib.Path(d) / "config_project.json"
            for text in ('{"project": ', "[]", "﻿{}", "null", '{"schema_version": 1e999}'):
                with self.subTest(text=text[:20]):
                    p.write_text(text, encoding="utf-8")
                    r = run("validate", "--config", p)
                    self.assertNotEqual(r.returncode, 0, r.stdout)
                    no_traceback(self, r)

    def test_C8_malformed_toml_gates_file_is_refused_with_a_message(self):
        with tempdir() as d:
            p = pathlib.Path(d) / "gates.toml"
            for text in ("[[gate]\nid = 1", "gate = 3", '[[gate]]\nid = "G1"\ntimeout = inf\n', "\x00\x01"):
                with self.subTest(text=text[:20]):
                    p.write_text(text, encoding="utf-8")
                    for args in (("gates", "validate", "--file", p), ("gates", "run", "--file", p)):
                        r = run(*args, cwd=d)
                        self.assertNotEqual(r.returncode, 0, r.stdout)
                        no_traceback(self, r)

    def test_C9_register_with_ragged_rows_is_checked_not_crashed(self):
        with tempdir() as d:
            reg = pathlib.Path(d) / "docs" / "register.md"
            reg.parent.mkdir()
            reg.write_text("# R\n\n" + HEADER + "| R-1 | CLOSED |\n| | | | | | | | | | | |\n|R-2|", encoding="utf-8")
            r = run("register", "check", "--file", reg, "--root", d)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            no_traceback(self, r)


class HostilePaths(unittest.TestCase):
    def test_C9_a_regression_test_path_outside_the_repo_does_not_count(self):
        # A CLOSED row whose test path climbs out of the repo found a file elsewhere and passed.
        with tempdir() as d:
            base = pathlib.Path(d)
            (base / "outside.py").write_text("x = 1\n", encoding="utf-8")
            repo = base / "repo"
            (repo / "docs").mkdir(parents=True)
            reg = repo / "docs" / "register.md"
            for test in ("../outside.py", str(base / "outside.py")):
                with self.subTest(test=test):
                    reg.write_text("# R\n\n" + HEADER + f"| R-1 | CLOSED | x | y | 1 | 0 | {test} | none: t |\n",
                                   encoding="utf-8")
                    r = run("register", "check", "--file", reg, "--root", repo)
                    self.assertEqual(r.returncode, 1, r.stdout)
                    self.assertIn("outside the repository", r.stdout)

    def test_C6_inspect_survives_a_symlink_loop_and_a_deep_tree(self):
        with tempdir() as d:
            repo = make_git_repo(pathlib.Path(d) / "repo", {"a.txt": "a\n"})
            deep = repo
            for i in range(60):
                deep = deep / f"d{i}"
            deep.mkdir(parents=True)
            (deep / "REGISTER.md").write_text("x\n", encoding="utf-8")
            try:
                (repo / "loop").symlink_to(repo, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            r = run("inspect", repo, "--max-depth", "100", timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            no_traceback(self, r)
            json.loads(r.stdout)

    def test_C6_hostile_file_names_do_not_break_inspect_or_doctor(self):
        names = ["spaces in name.md", "unicodé-ñame.py", "semi;colon.py", "$(touch pwned).py", "-rf.py"]
        with tempdir() as d:
            files = {n: "x = 1\n" for n in names}
            repo = make_git_repo(pathlib.Path(d) / "repo", files)
            (repo / "config_project.json").write_text(json.dumps(valid_config(repo__existing=True)), encoding="utf-8")
            for args in (("inspect", repo), ("doctor", "--repo", repo), ("classify", "--repo", repo)):
                with self.subTest(command=args[0]):
                    r = run(*args)
                    no_traceback(self, r)
            self.assertFalse((repo / "pwned").exists(), "a file name was executed")


class Output(unittest.TestCase):
    def test_C8_a_gate_with_enormous_output_is_judged_on_it(self):
        big = 'python -c "import sys; [print(\\"x\\" * 1000) for _ in range(20000)]; print(\\"FINDING BIG-1\\"); sys.exit(1)"'
        with tempdir() as d:
            p = pathlib.Path(d) / "gates.toml"
            p.write_text(f'[[gate]]\nid = "B1"\npurpose = "p"\nkind = "automated"\nrun = \'python -c "pass"\'\n'
                         f'pass = "exit 0"\ncontrol = \'{big}\'\ncontrol_expect = \'^FINDING BIG-1$\'\n', encoding="utf-8")
            r = run("gates", "run", "--controls", "--file", p, cwd=d, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("CONTROL RED", r.stdout)


class WindowsPaths(unittest.TestCase):
    def test_C18_chrysalis_home_with_spaces_and_backslashes_expands(self):
        with tempdir() as d:
            home = pathlib.Path(d) / "my tools" / "chrysalis"
            (home / "scripts").mkdir(parents=True)
            (home / "scripts" / "hello.py").write_text("print('FINDING HOME-OK')\nraise SystemExit(1)\n",
                                                        encoding="utf-8")
            p = pathlib.Path(d) / "gates.toml"
            p.write_text('[[gate]]\nid = "W1"\npurpose = "p"\nkind = "automated"\nrun = \'python -c "pass"\'\n'
                         'pass = "exit 0"\ncontrol = \'python "${CHRYSALIS_HOME}/scripts/hello.py"\'\n'
                         "control_expect = '^FINDING HOME-OK$'\n", encoding="utf-8")
            r = run("gates", "run", "--controls", "--file", p, cwd=d, env_extra={"CHRYSALIS_HOME": str(home)})
            self.assertEqual(r.returncode, 0, r.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows path forms")
    def test_C4_apply_handles_a_windows_long_or_unc_style_path(self):
        with tempdir() as d:
            repo = pathlib.Path(d) / "proj"
            repo.mkdir()
            cfg = write_config(pathlib.Path(d), valid_config())
            r = run("apply", "\\\\?\\" + str(repo), "--config", cfg, "--no-home")
            no_traceback(self, r)


if __name__ == "__main__":
    unittest.main()
