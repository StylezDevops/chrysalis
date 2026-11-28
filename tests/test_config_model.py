"""Spec tests for the config model (C3, C19): a schema version, four kinds of problem, migration
between versions, and deprecation. Only invalid and incomplete config blocks; dangerous and deprecated
config is reported every time it is checked but does not stop the work.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT, run, tempdir, valid_config, write_config, DELETE  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import project_config as pc  # noqa: E402


def kinds(cfg):
    return {k for k, _ in pc.problems(cfg)}


class Kinds(unittest.TestCase):
    def test_C19_a_valid_config_has_no_problems(self):
        self.assertEqual(pc.problems(valid_config()), [])

    def test_C19_each_problem_has_the_right_kind(self):
        cases = {
            "incomplete": [valid_config(risk__auth=DELETE), valid_config(schema_version=DELETE),
                           valid_config(project__name="")],
            "invalid": [valid_config(stage="sideways"), valid_config(surprise=1),
                        valid_config(stage="new", repo__existing=True), valid_config(schema_version="1")],
            "dangerous": [valid_config(stage="live", risk__live_production=True, ci__remote="none"),
                          valid_config(markers={"exempt": ["*.py"]}), valid_config(change={"small_lines": 300}),
                          valid_config(framework={"path": "/opt/chrysalis"}),
                          valid_config(agents__max_parallel_agents=8)],
        }
        for kind, cfgs in cases.items():
            for cfg in cfgs:
                with self.subTest(kind=kind, cfg=json.dumps(cfg)[:80]):
                    self.assertIn(kind, kinds(cfg), pc.problems(cfg))

    def test_C19_only_invalid_and_incomplete_block(self):
        with tempdir() as d:
            warn = write_config(pathlib.Path(d), valid_config(agents__max_parallel_agents=8))
            r = run("validate", "--config", warn)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("WARN [dangerous]", r.stdout)
            bad = write_config(pathlib.Path(d), valid_config(stage="sideways"))
            r = run("validate", "--config", bad)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("[invalid]", r.stdout)


class Versions(unittest.TestCase):
    def setUp(self):
        self.saved = (pc.SCHEMA_VERSION, dict(pc.MIGRATIONS), dict(pc.DEPRECATED))

    def tearDown(self):
        pc.SCHEMA_VERSION, pc.MIGRATIONS, pc.DEPRECATED = self.saved[0], self.saved[1], self.saved[2]

    def test_C19_a_newer_schema_is_refused_not_guessed_at(self):
        qs = pc.questions(valid_config(schema_version=pc.SCHEMA_VERSION + 1))
        self.assertTrue(any("newer Chrysalis" in q for q in qs), qs)

    def test_C19_an_older_schema_is_migrated_one_version_at_a_time(self):
        pc.SCHEMA_VERSION = 3
        pc.MIGRATIONS = {1: lambda c: {**c, "notes": "via 2"}, 2: lambda c: {**c, "notes": c["notes"] + ", via 3"}}
        old = valid_config(schema_version=1)
        self.assertTrue(any("config migrate" in q for q in pc.questions(old)))
        new, passed = pc.migrate(old)
        self.assertEqual(passed, [2, 3])
        self.assertEqual(new["schema_version"], 3)
        self.assertEqual(new["notes"], "via 2, via 3")
        self.assertEqual(pc.questions(new), [])

    def test_C19_a_version_raised_without_a_migration_fails_the_self_check(self):
        self.assertEqual(pc.migration_gaps(), [])
        pc.SCHEMA_VERSION = 2
        self.assertEqual(pc.migration_gaps(), ["schema_version 1 has no migration to 2"])
        with self.assertRaises(ValueError):
            pc.migrate(valid_config(schema_version=1))

    def test_C19_a_deprecated_field_warns_and_must_stay_in_the_schema(self):
        pc.DEPRECATED = {"notes": "free text moves to initial.md"}
        self.assertIn(("deprecated", "notes is deprecated: free text moves to initial.md"),
                      pc.problems(valid_config(notes="hello")))
        self.assertEqual(pc.questions(valid_config(notes="hello")), [], "a deprecated field blocked")
        pc.DEPRECATED = {"gone.field": "removed"}
        self.assertIn("deprecated field gone.field is not in the schema", pc.migration_gaps())

    def test_C19_migrate_command_writes_only_a_config_that_validates(self):
        with tempdir() as d:
            path = write_config(pathlib.Path(d), valid_config())
            r = run("config", "migrate", "--config", path)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("already at schema", r.stdout)


if __name__ == "__main__":
    unittest.main()
