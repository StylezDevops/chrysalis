"""Spec tests for the worktree commands and for every tool that picks a base branch (C12, U21).

Every test name carries the clause it proves (test_C4_...). tests/run_all.py --sweep relies on that:
each sabotage injection must make a test for its named clause fail.
"""

import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import LUSSER, git, make_git_repo, run, tempdir, valid_config  # noqa: E402



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


class BaseBranchFamily(unittest.TestCase):
    """U21: every tool that picks a base branch keeps the same promise (--base, then
    repo.default_branch, then main; an unreadable config fails closed). A tool added to MEMBERS
    later inherits these tests and fails until it keeps the promise. R-11 was lusser parts, missed
    when R-8 fixed worktree alone."""

    MEMBERS = {
        "worktree new": lambda repo, root: run("worktree", "new", "job-f", "--repo", repo, "--root", root),
        "worktree sweep": lambda repo, root: run("worktree", "sweep", "--repo", repo, "--root", root),
        "lusser parts": lambda repo, root: subprocess.run(
            [sys.executable, str(LUSSER), "parts"], cwd=repo, capture_output=True, text=True, encoding="utf-8"),
        "classify": lambda repo, root: run("classify", "--repo", repo),
    }
    # A complete config naming trunk: classify refuses to run on a config that does not validate.
    TRUNK_CONFIG = json.dumps(valid_config(repo__default_branch="trunk"))

    def setUp(self):
        self._tmp = tempdir()
        self.base = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def trunk_repo(self, name, config_text):
        repo = make_git_repo(self.base / name, {"a.txt": "a\n"})
        git(repo, "branch", "-m", "main", "trunk")
        (repo / "config_project.json").write_text(config_text, encoding="utf-8")
        return repo

    def test_C12_every_member_takes_its_base_from_the_config(self):
        for i, (member, call) in enumerate(self.MEMBERS.items()):
            with self.subTest(member=member):
                repo = self.trunk_repo(f"ok{i}", self.TRUNK_CONFIG)
                r = call(repo, self.base / f"wts{i}")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("trunk", r.stdout)
                self.assertIn("config_project.json", r.stdout, "the output does not say where the base came from")

    def test_C12_every_member_fails_closed_on_an_unreadable_config(self):
        for i, (member, call) in enumerate(self.MEMBERS.items()):
            with self.subTest(member=member):
                repo = self.trunk_repo(f"bad{i}", "{not json")
                r = call(repo, self.base / f"wts{i}")
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn("config_project.json", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
