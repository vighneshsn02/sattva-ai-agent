"""
Unit Tests for SATTVA Global CLI and Subcommands.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from sattva.cli.app import SattvaCLI, VERSION
from sattva.cli.installer import get_user_bin_dir, create_global_wrappers


class TestGlobalCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_version_string(self):
        self.assertEqual(VERSION, "1.1.0")

    def test_init_workspace(self):
        cli = SattvaCLI(workspace_path=self.temp_dir)
        cli.init_workspace()

        sattva_dir = Path(self.temp_dir) / ".sattva"
        self.assertTrue(sattva_dir.exists())
        self.assertTrue((sattva_dir / "config.json").exists())
        self.assertTrue((sattva_dir / "rules.md").exists())
        self.assertTrue((sattva_dir / ".gitignore").exists())

    def test_create_global_wrappers(self):
        user_bin = Path(self.temp_dir) / "bin"
        user_bin.mkdir(parents=True, exist_ok=True)
        repo_root = Path(__file__).parent.parent

        wrappers = create_global_wrappers(repo_root, user_bin)
        self.assertGreater(len(wrappers), 0)
        for w in wrappers:
            self.assertTrue(w.exists())


if __name__ == "__main__":
    unittest.main()
