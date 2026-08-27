"""
SATTVA AI AGENT — Multi-Agent Package.
Provides specialized autonomous agents (Planner, Coder, Tester, Reviewer, Security),
shared context memory, isolated workspace sandboxes, automated verification, and orchestrator synthesis.
"""

from sattva.agent.multi_agent.roles import (
    AgentRole,
    ROLE_METADATA,
    PLANNER_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    TESTER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    SECURITY_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
)
from sattva.agent.multi_agent.memory import (
    SharedMemory,
    TaskItem,
    SecurityFinding,
    ReviewItem,
    TestRunReport,
    ArtifactItem,
)
from sattva.agent.multi_agent.sandbox import WorkspaceSandbox
from sattva.agent.multi_agent.agents import (
    PlannerAgent,
    CoderAgent,
    TesterAgent,
    ReviewerAgent,
    SecurityAgent,
    AgentExecutionEvent,
)
from sattva.agent.multi_agent.verification import (
    VerificationEngine,
    VerificationResult,
)
from sattva.agent.multi_agent.orchestrator import (
    MultiAgentOrchestrator,
    MultiAgentEvent,
)

__all__ = [
    "AgentRole",
    "ROLE_METADATA",
    "PLANNER_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "TESTER_SYSTEM_PROMPT",
    "REVIEWER_SYSTEM_PROMPT",
    "SECURITY_SYSTEM_PROMPT",
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "SharedMemory",
    "TaskItem",
    "SecurityFinding",
    "ReviewItem",
    "TestRunReport",
    "ArtifactItem",
    "WorkspaceSandbox",
    "PlannerAgent",
    "CoderAgent",
    "TesterAgent",
    "ReviewerAgent",
    "SecurityAgent",
    "AgentExecutionEvent",
    "VerificationEngine",
    "VerificationResult",
    "MultiAgentOrchestrator",
    "MultiAgentEvent",
]
