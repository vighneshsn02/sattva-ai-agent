"""
Automated Result Verification Engine and Self-Healing Loop for SATTVA AI Multi-Agent Mode.
Coordinates Tester, Reviewer, and Security agents to validate staged artifacts before committing.
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel

from sattva.config import Config
from sattva.agent.multi_agent.roles import AgentRole
from sattva.agent.multi_agent.memory import SharedMemory, TaskItem
from sattva.agent.multi_agent.sandbox import WorkspaceSandbox
from sattva.agent.multi_agent.agents import (
    TesterAgent,
    ReviewerAgent,
    SecurityAgent,
    CoderAgent,
    AgentExecutionEvent,
)


class VerificationResult(BaseModel):
    passed: bool
    test_success: bool
    security_passed: bool
    review_passed: bool
    security_score: int
    review_score: int
    issues_summary: List[str] = []
    repair_needed: bool = False


class VerificationEngine:
    """
    Coordinates multi-dimensional verification of staged sandbox changes.
    Runs Tester, Reviewer, and Security agents concurrently, assesses results,
    and drives self-healing repair if defects are found.
    """

    def __init__(
        self,
        config: Config,
        tester: TesterAgent,
        reviewer: ReviewerAgent,
        security: SecurityAgent,
        coder: CoderAgent,
        max_repair_cycles: int = 2,
    ):
        self.config = config
        self.tester = tester
        self.reviewer = reviewer
        self.security = security
        self.coder = coder
        self.max_repair_cycles = max_repair_cycles

    async def verify_and_heal(
        self,
        memory: SharedMemory,
        sandbox: WorkspaceSandbox,
    ) -> AsyncGenerator[AgentExecutionEvent, None]:
        """
        Run the complete verification pipeline with automatic self-healing repair.
        Yields streaming events from all verifying agents.
        """
        cycle = 0

        while cycle <= self.max_repair_cycles:
            cycle += 1
            yield AgentExecutionEvent(
                agent_role=AgentRole.ORCHESTRATOR,
                event_type="thought",
                data={"chunk": f"\n🔍 Starting Automated Multi-Agent Verification (Cycle {cycle}/{self.max_repair_cycles + 1})...\n"},
            )

            # 1. Run Tester Verification
            async for event in self.tester.run_verification(memory, sandbox):
                yield event

            # 2. Run Security Audit
            async for event in self.security.scan_security(memory, sandbox):
                yield event

            # 3. Run Code Review
            async for event in self.reviewer.review_artifacts(memory, sandbox):
                yield event

            # Evaluate verification criteria
            v_result = self._evaluate_verification(memory)

            if v_result.passed:
                yield AgentExecutionEvent(
                    agent_role=AgentRole.ORCHESTRATOR,
                    event_type="thought",
                    data={
                        "chunk": f"✔ Verification Passed! (Security: {v_result.security_score}/100, Review: {v_result.review_score}/100, Tests: All OK)\n"
                    },
                )
                return

            # Verification failed — check if self-healing cycle is available
            if cycle <= self.max_repair_cycles:
                yield AgentExecutionEvent(
                    agent_role=AgentRole.ORCHESTRATOR,
                    event_type="thought",
                    data={
                        "chunk": f"⚠️ Verification detected issues:\n" + "\n".join(f"  - {iss}" for iss in v_result.issues_summary) + f"\nTriggering automated self-healing repair via Coder agent...\n"
                    },
                )

                # Create repair task
                repair_task = TaskItem(
                    id=f"repair_cycle_{cycle}",
                    title=f"Auto-fix verification issues (Cycle {cycle})",
                    role=AgentRole.CODER,
                    description="Fix the following issues detected during verification:\n" + "\n".join(f"- {iss}" for iss in v_result.issues_summary),
                    target_files=list(sandbox.staged_files.keys()),
                    dependencies=[],
                )

                # Execute repair
                async for event in self.coder.execute_task(repair_task, memory, sandbox):
                    yield event
            else:
                # Max cycles reached
                yield AgentExecutionEvent(
                    agent_role=AgentRole.ORCHESTRATOR,
                    event_type="thought",
                    data={"chunk": "Verification completed with warnings after maximum repair attempts.\n"},
                )
                return

    def _evaluate_verification(self, memory: SharedMemory) -> VerificationResult:
        """Evaluate whether staged changes pass quality, testing, and security gates."""
        issues = []

        # 1. Tests Gate
        test_success = True
        if memory.test_reports:
            for rep in memory.test_reports[-1:]:
                if not rep.success or rep.failed > 0:
                    test_success = False
                    issues.append(f"Test failures detected ({rep.failed} failed out of {rep.total}) in {rep.test_runner}")

        # 2. Security Gate
        security_passed = True
        critical_sec = [f for f in memory.security_findings if f.severity in ["CRITICAL", "HIGH"]]
        if critical_sec:
            security_passed = False
            for f in critical_sec:
                issues.append(f"Security Flaw [{f.severity}]: {f.description} at {f.file}:{f.line}")
        elif memory.security_score < 75:
            security_passed = False
            issues.append(f"Security score ({memory.security_score}/100) below acceptable threshold (75)")

        # 3. Review Gate
        review_passed = True
        if memory.reviews:
            latest_review = memory.reviews[-1]
            if latest_review.score < 60:
                review_passed = False
                issues.append(f"Review score ({latest_review.score}/100) below threshold (60): {', '.join(latest_review.recommendations[:2])}")

        passed = test_success and security_passed and review_passed

        return VerificationResult(
            passed=passed,
            test_success=test_success,
            security_passed=security_passed,
            review_passed=review_passed,
            security_score=memory.security_score,
            review_score=memory.review_score,
            issues_summary=issues,
            repair_needed=not passed,
        )
