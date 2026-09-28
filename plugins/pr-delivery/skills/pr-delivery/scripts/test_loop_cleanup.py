"""Provider import and API compatibility checks for shared loop cleanup."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
BUG_SCRIPTS = (SKILL_DIR.parents[2] / "bug-scrub-loop" / "skills" /
               "bug-scrub-loop" / "scripts")

if not BUG_SCRIPTS.is_dir():
    BUG_SCRIPTS = Path.home() / ".codex" / "skills" / "bug-scrub-loop" / "scripts"


class SharedCleanupProviderTests(unittest.TestCase):
    def run_python(self, code, env):
        return subprocess.run([sys.executable, "-c", code], env=env,
                              text=True, capture_output=True)

    def test_package_exposes_versioned_core_api(self):
        env = os.environ.copy()
        env["PR_DELIVERY_SKILL_DIR"] = str(SKILL_DIR)
        result = self.run_python(
            "from loop_cleanup import DELIVERY_CLEANUP_API_VERSION; "
            "from loop_cleanup import core; "
            "assert DELIVERY_CLEANUP_API_VERSION == 1 == core.DELIVERY_CLEANUP_API_VERSION; "
            "assert callable(core.validate_resource_transition)",
            env | {"PYTHONPATH": str(SCRIPTS)},
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_invalid_explicit_provider_fails_closed(self):
        env = os.environ.copy()
        env["PR_DELIVERY_SKILL_DIR"] = str(SKILL_DIR / "missing")
        result = self.run_python(
            "import shared_cleanup",
            env | {"PYTHONPATH": str(BUG_SCRIPTS)},
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("PR_DELIVERY_SKILL_DIR", result.stderr)


if __name__ == "__main__":
    unittest.main()
