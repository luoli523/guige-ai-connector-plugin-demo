"""Regression tests for OpenAI packaging checks, using disposable repo copies.

Run with Python 3.11+ and PyYAML: python scripts/test_check.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenAIPackagingChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="servicedesk-check-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        for folder in ("plugins", ".claude-plugin", ".agents", "scripts"):
            shutil.copytree(ROOT / folder, self.repo / folder)
        shutil.copytree(ROOT / "demo-services/common", self.repo / "demo-services/common")

    def run_check(self, expected_error=None):
        result = subprocess.run(
            [sys.executable, str(self.repo / "scripts/check.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1 if expected_error else 0, result.stdout + result.stderr)
        if expected_error:
            self.assertIn(expected_error, result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def change_json(self, relative, update):
        path = self.repo / relative
        data = json.loads(path.read_text())
        update(data)
        path.write_text(json.dumps(data))

    def test_valid_package(self):
        self.run_check()

    def test_missing_native_manifest(self):
        (self.repo / "plugins/servicedesk/.codex-plugin/plugin.json").unlink()
        self.run_check("JSON: plugins/servicedesk/.codex-plugin/plugin.json")

    def test_invalid_marketplace(self):
        for value in ("{", "[]", '{"plugins": [null]}'):
            with self.subTest(value=value):
                (self.repo / ".agents/plugins/marketplace.json").write_text(value)
                self.run_check("error(s)")

    def test_wrong_source_and_policy(self):
        self.change_json(".agents/plugins/marketplace.json", lambda data: data["plugins"][0].update(
            source="./plugins/servicedesk", policy={"installation": "TYPO"},
        ))
        self.run_check("expected local source")
        self.run_check("invalid installation/authentication policy")

    def test_version_and_reference_drift(self):
        self.change_json("plugins/servicedesk/.codex-plugin/plugin.json", lambda data: data.update(
            version="99.0.0", skills="./openai-skills/",
        ))
        self.run_check("name/version differ")
        self.run_check("skills must reference existing ./skills/")

    def test_missing_catalog_entry(self):
        self.change_json(".agents/plugins/marketplace.json", lambda data: data["plugins"].pop())
        self.run_check("plugin names/order differ")


if __name__ == "__main__":
    unittest.main()
