"""Real-input check for clause C1: the files METHOD.md cites exist in the source projects and say what
they are cited for.

Machine paths live in tests/evidence_roots.local.json (gitignored), for example:
  {"CHRYSOS": "D:/work/CHRYSOS", "MEMORY_CHRYSOS": "C:/Users/me/.claude/projects/<slug>/memory"}
Without that file the suite is skipped and says so; a skip is not a pass.
"""

import json
import pathlib
import re
import sys
import tomllib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402

MANIFEST = tomllib.loads((ROOT / "tests" / "evidence_manifest.toml").read_text(encoding="utf-8"))["cite"]
ROOTS_FILE = ROOT / "tests" / "evidence_roots.local.json"
METHOD = (ROOT / "METHOD.md").read_text(encoding="utf-8")


@unittest.skipUnless(ROOTS_FILE.exists(), "no tests/evidence_roots.local.json on this machine")
class Evidence(unittest.TestCase):
    roots = json.loads(ROOTS_FILE.read_text(encoding="utf-8")) if ROOTS_FILE.exists() else {}

    def test_C1_every_cited_file_exists_and_holds_its_quote(self):
        for cite in MANIFEST:
            with self.subTest(rule=cite["rule"], path=cite["path"]):
                base = self.roots.get(cite["project"])
                self.assertIsNotNone(base, f"no root configured for {cite['project']}")
                f = pathlib.Path(base) / cite["path"]
                self.assertTrue(f.is_file(), f"missing: {cite['project']}/{cite['path']}")
                if cite.get("quote"):
                    text = f.read_text(encoding="utf-8", errors="replace")
                    self.assertIn(cite["quote"], text, f"{cite['project']}/{cite['path']}")

    def test_C1_every_universal_rule_has_a_checked_citation(self):
        rules = set(re.findall(r"(?m)^### (U\d+)\.", METHOD))
        cited = {c["rule"] for c in MANIFEST}
        self.assertEqual(rules - cited, set())


class Manifest(unittest.TestCase):
    def test_C1_manifest_names_no_client_project(self):
        allowed = {"CHRYSOS", "MIDAS", "SUBSTRATE", "MEMORY_CHRYSOS", "MEMORY_MIDAS", "MEMORY_SUBSTRATE",
                   "PROJECTS_RULES"}
        self.assertEqual({c["project"] for c in MANIFEST} - allowed, set())


if __name__ == "__main__":
    unittest.main()
