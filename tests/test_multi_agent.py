"""
Unit Tests for SATTVA AI Multi-Agent Mode.
Tests Roles, SharedMemory, WorkspaceSandbox, Specialized Agents, VerificationEngine, and Orchestrator.
"""

import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path

from sattva.config import Config
from sattva.agent.multi_agent.roles import AgentRole, ROLE_METADATA
from sattva.agent.multi_agent.memory import (
    SharedMemory,
    TaskItem,
    SecurityFinding,
    ReviewItem,
    TestRunReport,
)
from sattva.agent.multi_agent.sandbox import WorkspaceSandbox
from sattva.agent.multi_agent.agents import (
    PlannerAgent,
    CoderAgent,
    TesterAgent,
    ReviewerAgent,
    SecurityAgent,
)
from sattva.agent.multi_agent.verification import VerificationEngine, VerificationResult
from sattva.agent.multi_agent.orchestrator import MultiAgentOrchestrator


class TestMultiAgentRolesAndMemory(unittest.TestCase):
    def test_roles_and_metadata(self):
        roles = [AgentRole.ORCHESTRATOR, AgentRole.PLANNER, AgentRole.CODER, AgentRole.TESTER, AgentRole.REVIEWER, AgentRole.SECURITY]
        for r in roles:
            self.assertIn(r, ROLE_METADATA)
            meta = ROLE_METADATA[r]
            self.assertIn("title", meta)
            self.assertIn("icon", meta)
            self.assertIn("description", meta)

    def test_shared_memory_plan_and_ready_tasks(self):
        async def _run():
            mem = SharedMemory(user_goal="Build a REST API", workspace_path=".")
            await mem.set_plan(
                architecture_summary="FastAPI backend with tests",
                tech_stack=["Python", "FastAPI"],
                tasks=[
                    {"id": "t1", "title": "Setup app", "role": "coder", "dependencies": []},
                    {"id": "t2", "title": "Add routes", "role": "coder", "dependencies": ["t1"]},
                    {"id": "t3", "title": "Add tests", "role": "tester", "dependencies": ["t2"]},
                ],
            )
            self.assertEqual(len(mem.tasks), 3)

            # Initially only t1 has no dependencies
            ready = await mem.get_ready_tasks()
            self.assertEqual(len(ready), 1)
            self.assertEqual(ready[0].id, "t1")

            # Complete t1
            await mem.update_task_status("t1", status="completed")
            ready = await mem.get_ready_tasks()
            self.assertEqual(len(ready), 1)
            self.assertEqual(ready[0].id, "t2")

            # Complete t2
            await mem.update_task_status("t2", status="completed")
            ready = await mem.get_ready_tasks()
            self.assertEqual(len(ready), 1)
            self.assertEqual(ready[0].id, "t3")

            # Complete t3
            await mem.update_task_status("t3", status="completed")
            has_more = await mem.has_unfinished_tasks()
            self.assertFalse(has_more)

        asyncio.run(_run())

    def test_security_score_calculation(self):
        async def _run():
            mem = SharedMemory(user_goal="Test security", workspace_path=".")
            self.assertEqual(mem.security_score, 100)

            # Add critical finding
            await mem.add_security_finding(
                SecurityFinding(
                    rule_id="AWS_KEY",
                    severity="CRITICAL",
                    file="config.py",
                    line=10,
                    description="AWS Key leaked",
                    remediation="Use env vars",
                )
            )
            self.assertEqual(mem.security_score, 65)  # 100 - 35 = 65

            # Add high finding
            await mem.add_security_finding(
                SecurityFinding(
                    rule_id="SQLI",
                    severity="HIGH",
                    file="db.py",
                    line=25,
                    description="SQL injection",
                    remediation="Use parameterized query",
                )
            )
            self.assertEqual(mem.security_score, 45)  # 65 - 20 = 45

        asyncio.run(_run())


class TestWorkspaceSandbox(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create a base file
        self.base_file = Path(self.temp_dir) / "app.py"
        self.base_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sandbox_stage_create_and_commit(self):
        sandbox = WorkspaceSandbox(base_workspace=self.temp_dir)
        try:
            # Stage a new file
            res = sandbox.stage_file_create("utils/helper.py", "def add(a, b):\n    return a + b\n")
            self.assertEqual(res["action"], "created")
            self.assertIn("utils/helper.py", sandbox.staged_files)

            # Check that base workspace does not have utils/helper.py yet
            self.assertFalse((Path(self.temp_dir) / "utils" / "helper.py").exists())

            # Read from sandbox
            content = sandbox.read_file("utils/helper.py")
            self.assertIn("def add(a, b):", content)

            # Commit to base workspace
            committed = sandbox.commit_to_workspace()
            self.assertEqual(len(committed), 1)
            self.assertTrue((Path(self.temp_dir) / "utils" / "helper.py").exists())
            self.assertEqual((Path(self.temp_dir) / "utils" / "helper.py").read_text(), "def add(a, b):\n    return a + b\n")
        finally:
            sandbox.cleanup()

    def test_sandbox_stage_edit(self):
        sandbox = WorkspaceSandbox(base_workspace=self.temp_dir)
        try:
            # Stage edit on app.py
            res = sandbox.stage_file_edit(
                "app.py",
                target_content="return 'world'",
                replacement_content="return 'sattva'",
            )
            self.assertEqual(res["action"], "modified")
            self.assertIn("+    return 'sattva'", res["diff"])

            # Base file is still untouched
            self.assertEqual(self.base_file.read_text(encoding="utf-8"), "def hello():\n    return 'world'\n")

            # Sandboxed read returns modified version
            self.assertEqual(sandbox.read_file("app.py"), "def hello():\n    return 'sattva'\n")

            # Commit changes
            sandbox.commit_to_workspace()
            self.assertEqual(self.base_file.read_text(encoding="utf-8"), "def hello():\n    return 'sattva'\n")
        finally:
            sandbox.cleanup()


class TestSecurityAgentDeterministicScanning(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_secrets_and_vulnerabilities(self):
        async def _run():
            sandbox = WorkspaceSandbox(base_workspace=self.temp_dir)
            try:
                # Stage file with hardcoded key and eval
                bad_code = """import os
API_KEY = "AIzaSyD-1234567890abcdefghijklmn"
def run_user_input(code_str):
    eval(code_str)
"""
                sandbox.stage_file_create("insecure.py", bad_code)

                mem = SharedMemory(user_goal="Check code", workspace_path=self.temp_dir)
                sec_agent = SecurityAgent(config=Config(self.temp_dir))

                events = []
                async for ev in sec_agent.scan_security(mem, sandbox):
                    events.append(ev)

                self.assertGreater(len(mem.security_findings), 0)
                rule_ids = [f.rule_id for f in mem.security_findings]
                self.assertIn("HARDCODED_API_KEY", rule_ids)
                self.assertIn("INSECURE_EVAL", rule_ids)
                self.assertLess(mem.security_score, 80)
            finally:
                sandbox.cleanup()

        asyncio.run(_run())


class TestVerificationEngine(unittest.TestCase):
    def test_evaluate_verification_pass_and_fail(self):
        mem = SharedMemory(user_goal="Test", workspace_path=".")
        config = Config()
        v_engine = VerificationEngine(
            config=config,
            tester=TesterAgent(config),
            reviewer=ReviewerAgent(config),
            security=SecurityAgent(config),
            coder=CoderAgent(config),
        )

        # 1. Clean memory
        res = v_engine._evaluate_verification(mem)
        self.assertTrue(res.passed)

        # 2. Add failing test report
        async def _test_fail():
            await mem.add_test_report(
                TestRunReport(test_runner="pytest", total=5, passed=3, failed=2, success=False)
            )
            res_fail = v_engine._evaluate_verification(mem)
            self.assertFalse(res_fail.passed)
            self.assertTrue(res_fail.repair_needed)
            self.assertIn("Test failures detected", res_fail.issues_summary[0])

        asyncio.run(_test_fail())


if __name__ == "__main__":
    unittest.main()
