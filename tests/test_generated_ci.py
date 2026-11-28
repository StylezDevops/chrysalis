"""Spec tests for what apply generates for CI and other machines (C17, C18): the workflow follows
ci.remote and runs the project's gates, generated files name no machine path, the framework is pinned
to an immutable commit or apply refuses, and every GitHub Action is pinned to a commit SHA.
"""

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT, run, tempdir, valid_config, write_config  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import scaffold  # noqa: E402

WORKFLOW = ".github/workflows/chrysalis.yml"
SHA = re.compile(r"^[0-9a-f]{40}$")


def apply_new(d, **overrides):
    repo = pathlib.Path(d) / "proj"
    repo.mkdir()
    cfg = write_config(pathlib.Path(d), valid_config(**overrides))
    return repo, run("apply", repo, "--config", cfg, "--no-home")


class Workflow(unittest.TestCase):
    def test_C17_the_workflow_follows_ci_remote(self):
        with tempdir() as d:
            repo, r = apply_new(d, ci__remote="none")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertFalse((repo / WORKFLOW).exists(), "ci.remote none still got a workflow")
        with tempdir() as d:
            repo, _ = apply_new(d, ci__remote="on-request")
            text = (repo / WORKFLOW).read_text(encoding="utf-8")
            on = text.split("\non:", 1)[1].split("\npermissions:", 1)[0]
            self.assertIn("workflow_dispatch", on)
            self.assertNotIn("pull_request", on)
            self.assertNotIn("push:", on)
        with tempdir() as d:
            repo, _ = apply_new(d, ci__remote="every-push")
            on = (repo / WORKFLOW).read_text(encoding="utf-8").split("\non:", 1)[1].split("\npermissions:", 1)[0]
            self.assertIn("pull_request", on)
            self.assertIn("push:", on)

    def test_C17_the_workflow_runs_the_projects_gates_and_controls(self):
        with tempdir() as d:
            repo, _ = apply_new(d, ci__remote="every-push")
            text = (repo / WORKFLOW).read_text(encoding="utf-8")
        for step in ("gates validate", "gates run --file gates.toml", "gates run --controls --file gates.toml"):
            self.assertIn(step, text)

    def test_C18_generated_files_name_no_machine_path(self):
        with tempdir() as d:
            repo, r = apply_new(d, ci__remote="every-push")
            self.assertEqual(r.returncode, 0, r.stdout)
            for f in repo.rglob("*"):
                if f.is_file() and ".chrysalis" not in f.relative_to(repo).parts:
                    with self.subTest(file=f.name):
                        text = f.read_text(encoding="utf-8")
                        self.assertNotIn(str(ROOT), text)
                        self.assertNotIn(ROOT.as_posix(), text)
            self.assertIn("${CHRYSALIS_HOME}", (repo / "AGENTS.md").read_text(encoding="utf-8"))

    def test_C18_generated_gates_run_without_setting_chrysalis_home(self):
        with tempdir() as d:
            repo, _ = apply_new(d)
            gates = repo / "gates.toml"
            r = run("gates", "run", "--controls", "--file", gates, "--only", "R1", cwd=repo,
                    env_extra={"CHRYSALIS_HOME": ""})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("CONTROL RED", r.stdout)


ACTIONLINT = "rhysd/actionlint@sha256:887a259a5a534f3c4f36cb02dca341673c6089431057242cdc931e9f133147e9"


def rendered_workflow(d) -> pathlib.Path:
    repo, r = apply_new(d, ci__remote="every-push")
    assert r.returncode == 0, r.stdout
    return repo / WORKFLOW


def linux_docker() -> bool:
    import shutil
    import subprocess
    if shutil.which("docker") is None:
        return False
    r = subprocess.run(["docker", "info", "--format", "{{.OSType}}"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "linux"


class Permissions(unittest.TestCase):
    """Least privilege as a tested invariant: both workflows grant the token read access to contents and
    nothing else, at the top level, and no job widens it."""

    def check(self, text, name):
        top = re.search(r"(?m)^permissions:\r?\n((?:[ ]+\S[^\n]*\n)+)", text)
        self.assertIsNotNone(top, f"{name} has no top-level permissions block")
        self.assertEqual(top.group(1).split(), ["contents:", "read"], f"{name}: {top.group(1)!r}")
        self.assertNotRegex(text, r"(?m):\s*write\b", f"{name} grants a write permission")
        self.assertNotRegex(text, r"(?m)^\s+permissions:\s*write-all", f"{name} grants write-all")
        self.assertEqual(len(re.findall(r"(?m)^\s*permissions:", text)), 1, f"{name}: a job sets its own permissions")

    def test_C17_workflows_grant_read_only_contents(self):
        self.check((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"), "ci.yml")
        with tempdir() as d:
            self.check(rendered_workflow(d).read_text(encoding="utf-8"), "generated chrysalis.yml")

    def test_C17_actionlint_accepts_both_workflows(self):
        if not linux_docker():
            self.skipTest("no Docker with Linux containers on this machine")
        import subprocess
        with tempdir() as d:
            gen = rendered_workflow(d)
            for f in (ROOT / ".github" / "workflows" / "ci.yml", gen):
                with self.subTest(workflow=f.name):
                    r = subprocess.run(["docker", "run", "--rm", "-v", f"{f.parent.resolve().as_posix()}:/w:ro",
                                        ACTIONLINT, "-color=false", f"/w/{f.name}"],
                                       capture_output=True, text=True, encoding="utf-8", timeout=300)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Pinning(unittest.TestCase):
    def test_C17_the_framework_is_pinned_to_a_commit_or_apply_refuses(self):
        real = scaffold.git_run
        try:
            scaffold.git_run = lambda *a: (128, "fatal: not a git repository")
            scaffold.framework_ref.cache_clear()
            with tempdir() as d:
                _, actions = scaffold.plan(pathlib.Path(d), valid_config(ci__remote="every-push"), "x")
        finally:
            scaffold.git_run = real
            scaffold.framework_ref.cache_clear()
        refused = [a for a in actions if a[0] == "REFUSE"]
        self.assertEqual([a[1] for a in refused], [WORKFLOW], actions)
        self.assertIn("framework.ref", refused[0][2])

    def test_C17_framework_ref_must_be_a_full_commit(self):
        from project_config import questions
        self.assertTrue(any("framework.ref" in q for q in questions(valid_config(framework={"ref": "main"}))))
        self.assertEqual(questions(valid_config(framework={"ref": "a" * 40})), [])

    def test_C17_every_action_is_pinned_to_a_commit_sha(self):
        for f in (ROOT / ".github" / "workflows" / "ci.yml", ROOT / "templates" / "ci-chrysalis.yml"):
            for ref in re.findall(r"uses:\s*[\w./-]+@(\S+)", f.read_text(encoding="utf-8")):
                with self.subTest(file=f.name, ref=ref):
                    self.assertRegex(ref, SHA)


if __name__ == "__main__":
    unittest.main()
