"""
Unit tests for SATTVA AI AGENT tools and components.
"""

import os
import shutil
import tempfile
import asyncio
import unittest
from pathlib import Path

from sattva.tools import (
    create_default_registry,
    CreateFileTool,
    ReadFileTool,
    EditFileTool,
    InsertCodeTool,
    ScanCodebaseTool,
    SearchCodeTool,
    FindFilesTool,
    RunCommandTool,
)


class TestSattvaTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="sattva_test_")
        self.workspace = Path(self.test_dir)
        self.registry = create_default_registry(str(self.workspace))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_create_and_read(self):
        async def _run():
            # 1. Create file
            res = await self.registry.execute(
                "create_file",
                {"file_path": "src/app.py", "content": "def hello():\n    return 'world'\n"},
            )
            self.assertTrue(res.success)
            self.assertTrue((self.workspace / "src" / "app.py").exists())

            # 2. Read file
            read_res = await self.registry.execute("read_file", {"file_path": "src/app.py"})
            self.assertTrue(read_res.success)
            self.assertIn("def hello():", read_res.data["content"])

        asyncio.run(_run())

    def test_file_editing_and_diff(self):
        async def _run():
            # Create file
            await self.registry.execute(
                "create_file",
                {"file_path": "calculator.py", "content": "def add(a, b):\n    return a - b\n"},
            )

            # Edit file (fix bug)
            edit_res = await self.registry.execute(
                "edit_file",
                {
                    "file_path": "calculator.py",
                    "target_content": "return a - b",
                    "replacement_content": "return a + b",
                },
            )
            self.assertTrue(edit_res.success)
            self.assertIn("+    return a + b", edit_res.data["diff"])
            self.assertIn("-    return a - b", edit_res.data["diff"])

            # Verify on disk
            content = (self.workspace / "calculator.py").read_text(encoding="utf-8")
            self.assertEqual(content, "def add(a, b):\n    return a + b\n")

        asyncio.run(_run())

    def test_codebase_scanner(self):
        async def _run():
            # Create a couple files with AST symbols
            await self.registry.execute(
                "create_file",
                {
                    "file_path": "services/auth.py",
                    "content": "class AuthService:\n    def login(self, user):\n        pass\n\ndef generate_token():\n    return 'xyz'\n",
                },
            )

            scan_res = await self.registry.execute("scan_codebase", {"target_dir": "."})
            self.assertTrue(scan_res.success)
            self.assertEqual(scan_res.data["total_files"], 1)
            self.assertIn("AuthService", str(scan_res.data["symbols"]))
            self.assertIn("generate_token", str(scan_res.data["symbols"]))

        asyncio.run(_run())

    def test_search_code_and_find_files(self):
        async def _run():
            await self.registry.execute(
                "create_file",
                {"file_path": "main.py", "content": "import sys\n# TODO: Implement database connection\n"},
            )

            search_res = await self.registry.execute("search_code", {"query": "TODO", "path": "."})
            self.assertTrue(search_res.success)
            self.assertEqual(search_res.data["count"], 1)
            self.assertEqual(search_res.data["matches"][0]["line_number"], 2)

            find_res = await self.registry.execute("find_files", {"pattern": "*.py"})
            self.assertTrue(find_res.success)
            self.assertIn("main.py", find_res.data["files"])

        asyncio.run(_run())

    def test_run_command(self):
        async def _run():
            res = await self.registry.execute("run_command", {"command": "python -c \"print('Sattva-OK')\""})
            self.assertTrue(res.success)
            self.assertIn("Sattva-OK", res.data["stdout"])

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
