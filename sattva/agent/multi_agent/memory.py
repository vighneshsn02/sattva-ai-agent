"""
Shared Context and Blackboard Memory for SATTVA AI Multi-Agent System.
Allows asynchronous, thread-safe communication, knowledge sharing, and artifact tracking among agents.
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from sattva.agent.multi_agent.roles import AgentRole, ROLE_METADATA


class TaskItem(BaseModel):
    id: str
    title: str
    role: AgentRole
    description: str
    target_files: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"  # "pending", "running", "verifying", "completed", "failed", "skipped"
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SecurityFinding(BaseModel):
    rule_id: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    file: str
    line: Optional[int] = None
    description: str
    remediation: str


class ReviewItem(BaseModel):
    score: int  # 0 - 100
    verdict: str  # "APPROVED", "NEEDS_IMPROVEMENT", "REJECTED"
    strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    detailed_feedback: Optional[str] = None


class TestRunReport(BaseModel):
    test_runner: str = "pytest"
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    output_log: str = ""
    success: bool = True


class ArtifactItem(BaseModel):
    path: str
    action: str  # "created", "modified", "deleted"
    diff: Optional[str] = None
    staged: bool = True
    verified: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SharedMemory:
    """
    Central Blackboard / Shared Memory storing execution graph, staged artifacts,
    test results, security findings, review notes, and knowledge base.
    """

    def __init__(self, user_goal: str = "", workspace_path: str = "."):
        self.user_goal = user_goal
        self.workspace_path = workspace_path
        self.created_at = datetime.now().isoformat()
        self._lock = asyncio.Lock()

        # Architecture & Plan
        self.architecture_summary: str = ""
        self.tech_stack: List[str] = []
        self.tasks: Dict[str, TaskItem] = {}

        # Shared Knowledge & Artifacts
        self.knowledge: Dict[str, Any] = {}
        self.artifacts: Dict[str, ArtifactItem] = {}

        # Quality & Verification
        self.test_reports: List[TestRunReport] = []
        self.security_findings: List[SecurityFinding] = []
        self.security_score: int = 100
        self.reviews: List[ReviewItem] = []
        self.review_score: int = 100

        # Event Log
        self.events_log: List[Dict[str, Any]] = []

    async def set_plan(self, architecture_summary: str, tech_stack: List[str], tasks: List[Dict[str, Any]]) -> None:
        """Register the architectural plan and initial tasks."""
        async with self._lock:
            self.architecture_summary = architecture_summary
            self.tech_stack = tech_stack
            self.tasks.clear()
            for t in tasks:
                task_id = t.get("id") or f"task_{len(self.tasks) + 1}"
                role_val = t.get("role", "coder").lower()
                try:
                    role_enum = AgentRole(role_val)
                except ValueError:
                    role_enum = AgentRole.CODER

                self.tasks[task_id] = TaskItem(
                    id=task_id,
                    title=t.get("title", f"Task {task_id}"),
                    role=role_enum,
                    description=t.get("description", ""),
                    target_files=t.get("target_files", []),
                    dependencies=t.get("dependencies", []),
                    status="pending",
                )
            self.log_event("plan_set", {
                "tasks_count": len(self.tasks),
                "architecture_summary": architecture_summary,
            })

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update task execution lifecycle status."""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status
                if status == "running" and not task.started_at:
                    task.started_at = datetime.now().isoformat()
                elif status in ["completed", "failed", "skipped"]:
                    task.completed_at = datetime.now().isoformat()
                if result:
                    task.result = result
                if error:
                    task.error = error

                self.log_event("task_updated", {
                    "task_id": task_id,
                    "status": status,
                    "result_preview": (result[:80] + "...") if result and len(result) > 80 else result,
                    "error": error,
                })

    async def get_ready_tasks(self) -> List[TaskItem]:
        """Find pending tasks whose dependencies have all completed successfully."""
        async with self._lock:
            ready = []
            for task in self.tasks.values():
                if task.status != "pending":
                    continue
                deps_met = True
                for dep_id in task.dependencies:
                    dep = self.tasks.get(dep_id)
                    if not dep or dep.status != "completed":
                        deps_met = False
                        break
                if deps_met:
                    ready.append(task)
            return ready

    async def has_unfinished_tasks(self) -> bool:
        """Check if any task is still pending or running."""
        async with self._lock:
            return any(t.status in ["pending", "running", "verifying"] for t in self.tasks.values())

    async def record_artifact(self, path: str, action: str, diff: Optional[str] = None, staged: bool = True) -> None:
        """Record or update a generated/modified file artifact."""
        async with self._lock:
            self.artifacts[path] = ArtifactItem(
                path=path,
                action=action,
                diff=diff,
                staged=staged,
                verified=False,
            )
            self.log_event("artifact_recorded", {"path": path, "action": action, "has_diff": diff is not None})

    async def add_test_report(self, report: TestRunReport) -> None:
        """Record a test execution report."""
        async with self._lock:
            self.test_reports.append(report)
            self.log_event("test_report_added", {
                "success": report.success,
                "passed": report.passed,
                "failed": report.failed,
                "total": report.total,
            })

    async def add_security_finding(self, finding: SecurityFinding) -> None:
        """Record a security finding and update the composite security score."""
        async with self._lock:
            self.security_findings.append(finding)
            # Recalculate score based on severity penalty
            penalties = {
                "CRITICAL": 35,
                "HIGH": 20,
                "MEDIUM": 10,
                "LOW": 5,
                "INFO": 0,
            }
            total_penalty = sum(penalties.get(f.severity.upper(), 5) for f in self.security_findings)
            self.security_score = max(0, 100 - total_penalty)

    async def add_review(self, review: ReviewItem) -> None:
        """Record code review feedback and update average review score."""
        async with self._lock:
            self.reviews.append(review)
            avg_score = int(sum(r.score for r in self.reviews) / len(self.reviews))
            self.review_score = avg_score

    async def set_knowledge(self, key: str, value: Any) -> None:
        """Store arbitrary shared knowledge in blackboard."""
        async with self._lock:
            self.knowledge[key] = value

    async def get_knowledge(self, key: str, default: Any = None) -> Any:
        """Retrieve shared knowledge by key."""
        async with self._lock:
            return self.knowledge.get(key, default)

    def log_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Log chronological agent event."""
        self.events_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_name,
            "data": payload,
        })

    def get_context_snapshot(self) -> Dict[str, Any]:
        """Produce a complete snapshot for agents or UI serialization."""
        return {
            "user_goal": self.user_goal,
            "workspace_path": self.workspace_path,
            "architecture_summary": self.architecture_summary,
            "tech_stack": self.tech_stack,
            "tasks": [t.model_dump() for t in self.tasks.values()],
            "artifacts": [a.model_dump() for a in self.artifacts.values()],
            "test_reports": [r.model_dump() for r in self.test_reports],
            "security_findings": [f.model_dump() for f in self.security_findings],
            "security_score": self.security_score,
            "reviews": [r.model_dump() for r in self.reviews],
            "review_score": self.review_score,
            "knowledge": self.knowledge,
        }

    def generate_markdown_summary(self) -> str:
        """Generate a formatted markdown report of the entire multi-agent execution."""
        lines = []
        lines.append(f"## ⚡ Multi-Agent Execution Summary\n")
        lines.append(f"**Goal:** {self.user_goal}\n")
        if self.architecture_summary:
            lines.append(f"### 🏗️ Architecture & Strategy\n{self.architecture_summary}\n")
        if self.tech_stack:
            lines.append(f"**Tech Stack:** {', '.join(self.tech_stack)}\n")

        # Tasks Table
        lines.append("### 📋 Executed Tasks")
        lines.append("| ID | Task | Assigned Agent | Status | Target Files |")
        lines.append("|---|---|---|---|---|")
        for t in self.tasks.values():
            role_meta = ROLE_METADATA.get(t.role, {})
            icon = role_meta.get("icon", "🤖")
            status_icon = "✔" if t.status == "completed" else ("✘" if t.status == "failed" else "●")
            files_str = ", ".join(t.target_files) if t.target_files else "—"
            lines.append(f"| `{t.id}` | {t.title} | {icon} {t.role.value.capitalize()} | {status_icon} {t.status.capitalize()} | `{files_str}` |")
        lines.append("")

        # Artifacts
        if self.artifacts:
            lines.append("### 📁 Modified & Created Artifacts")
            for a in self.artifacts.values():
                action_badge = "[Created]" if a.action == "created" else f"[{a.action.capitalize()}]"
                lines.append(f"- **`{a.path}`** {action_badge}")
            lines.append("")

        # Verification Scores
        lines.append("### 🛡️ Quality & Verification Scorecard")
        test_status = "All Passed ✔" if self.test_reports and all(r.success for r in self.test_reports) else ("Failed ✘" if self.test_reports else "No tests run")
        lines.append(f"- **Test Suite Status:** `{test_status}`")
        lines.append(f"- **Security Score:** `{self.security_score}/100` ({len(self.security_findings)} findings)")
        lines.append(f"- **Code Review Score:** `{self.review_score}/100`")
        lines.append("")

        if self.security_findings:
            lines.append("#### ⚠️ Security Findings:")
            for f in self.security_findings:
                lines.append(f"- **[{f.severity}]** `{f.file}:{f.line or 'N/A'}` — {f.description} (Remediation: {f.remediation})")
            lines.append("")

        if self.reviews:
            lines.append("#### 🧐 Review Recommendations:")
            for r in self.reviews:
                for rec in r.recommendations:
                    lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)
