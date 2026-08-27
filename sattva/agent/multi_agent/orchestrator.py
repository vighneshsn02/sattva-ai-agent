"""
Master Multi-Agent Orchestrator for SATTVA AI AGENT.
Coordinates specialized agents (Planner, Coder, Tester, Reviewer, Security),
manages parallel task DAG execution, shared memory, sandbox isolation, automated verification, and final synthesis.
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field

from sattva.config import Config
from sattva.ollama_client import OllamaClient
from sattva.agent.session import Session
from sattva.agent.multi_agent.roles import (
    AgentRole,
    ROLE_METADATA,
    ORCHESTRATOR_SYSTEM_PROMPT,
)
from sattva.agent.multi_agent.memory import SharedMemory, TaskItem
from sattva.agent.multi_agent.sandbox import WorkspaceSandbox
from sattva.agent.multi_agent.agents import (
    PlannerAgent,
    CoderAgent,
    TesterAgent,
    ReviewerAgent,
    SecurityAgent,
    AgentExecutionEvent,
)
from sattva.agent.multi_agent.verification import VerificationEngine


class MultiAgentEvent(BaseModel):
    event_type: str  # "pipeline_stage", "agent_start", "agent_thought", "agent_tool_start", "agent_tool_end", "agent_completed", "verification", "diff_ready", "synthesis_chunk", "done", "error"
    role: Optional[AgentRole] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class MultiAgentOrchestrator:
    """
    Coordinates end-to-end multi-agent execution pipeline.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        workspace_path: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.config = config or Config(workspace_path)
        self.workspace_path = str(self.config.workspace_path)
        self.model = model or self.config.default_model
        self.ollama = OllamaClient(base_url=self.config.ollama_url)

        # Initialize specialized domain agents
        self.planner = PlannerAgent(self.config, self.ollama, self.model)
        self.coder = CoderAgent(self.config, self.ollama, self.model)
        self.tester = TesterAgent(self.config, self.ollama, self.model)
        self.reviewer = ReviewerAgent(self.config, self.ollama, self.model)
        self.security = SecurityAgent(self.config, self.ollama, self.model)

        self.verification_engine = VerificationEngine(
            config=self.config,
            tester=self.tester,
            reviewer=self.reviewer,
            security=self.security,
            coder=self.coder,
            max_repair_cycles=2,
        )

    def set_model(self, model_name: str) -> None:
        self.model = model_name
        self.planner.model = model_name
        self.coder.model = model_name
        self.tester.model = model_name
        self.reviewer.model = model_name
        self.security.model = model_name

    def set_workspace(self, workspace_path: str) -> None:
        self.workspace_path = workspace_path
        self.config.workspace_path = workspace_path

    async def run(
        self,
        user_message: str,
        session: Optional[Session] = None,
    ) -> AsyncGenerator[MultiAgentEvent, None]:
        """
        Execute full autonomous multi-agent orchestration lifecycle.
        Yields rich real-time MultiAgentEvent stream.
        """
        if session is None:
            session = Session(model=self.model, workspace_path=self.workspace_path)

        session.add_message(role="user", content=user_message)

        # 1. Initialize Shared Context & Sandbox
        memory = SharedMemory(user_goal=user_message, workspace_path=self.workspace_path)
        sandbox = WorkspaceSandbox(base_workspace=self.workspace_path)

        yield MultiAgentEvent(
            event_type="pipeline_stage",
            role=AgentRole.ORCHESTRATOR,
            data={
                "stage": "INIT",
                "title": "Initializing Multi-Agent Team",
                "model": self.model,
                "workspace": self.workspace_path,
                "team": [
                    {"role": r.value, "title": meta["title"], "icon": meta["icon"], "description": meta["description"]}
                    for r, meta in ROLE_METADATA.items()
                ],
            },
        )

        try:
            # ==========================================
            # STAGE 1: PLANNING & ARCHITECTURE
            # ==========================================
            yield MultiAgentEvent(
                event_type="pipeline_stage",
                role=AgentRole.PLANNER,
                data={"stage": "PLANNING", "title": "Deconstructing Goal & Task DAG"},
            )

            async for event in self.planner.create_plan(user_message, memory):
                yield self._map_agent_event(event)

            # ==========================================
            # STAGE 2: PARALLEL TASK EXECUTION
            # ==========================================
            yield MultiAgentEvent(
                event_type="pipeline_stage",
                role=AgentRole.ORCHESTRATOR,
                data={
                    "stage": "EXECUTION",
                    "title": "Executing Tasks (Parallel & Sandboxed)",
                    "tasks_count": len(memory.tasks),
                    "tasks": [t.model_dump() for t in memory.tasks.values()],
                },
            )

            # Execute tasks in dependency waves (parallel execution of ready tasks)
            max_waves = 10
            wave = 0

            while await memory.has_unfinished_tasks() and wave < max_waves:
                wave += 1
                ready_tasks = await memory.get_ready_tasks()

                if not ready_tasks:
                    # Circular dependency or stalled tasks — mark remaining as ready
                    for t in memory.tasks.values():
                        if t.status == "pending":
                            ready_tasks.append(t)
                            break
                    if not ready_tasks:
                        break

                # Execute ready tasks in parallel wave
                yield MultiAgentEvent(
                    event_type="pipeline_stage",
                    role=AgentRole.ORCHESTRATOR,
                    data={
                        "stage": "PARALLEL_WAVE",
                        "wave": wave,
                        "running_tasks": [t.id for t in ready_tasks],
                    },
                )

                # Helper to run an individual task and stream its events
                async def _run_single_task(t_item: TaskItem):
                    await memory.update_task_status(t_item.id, status="running")
                    agent_events = []
                    if t_item.role == AgentRole.CODER:
                        async for ev in self.coder.execute_task(t_item, memory, sandbox):
                            agent_events.append(ev)
                    elif t_item.role == AgentRole.TESTER:
                        async for ev in self.tester.run_verification(memory, sandbox):
                            agent_events.append(ev)
                    elif t_item.role == AgentRole.REVIEWER:
                        async for ev in self.reviewer.review_artifacts(memory, sandbox):
                            agent_events.append(ev)
                    elif t_item.role == AgentRole.SECURITY:
                        async for ev in self.security.scan_security(memory, sandbox):
                            agent_events.append(ev)
                    else:
                        async for ev in self.coder.execute_task(t_item, memory, sandbox):
                            agent_events.append(ev)
                    return agent_events

                # Run parallel tasks
                task_futures = [_run_single_task(task) for task in ready_tasks]
                results = await asyncio.gather(*task_futures, return_exceptions=True)

                for r in results:
                    if isinstance(r, list):
                        for ev in r:
                            yield self._map_agent_event(ev)
                            # Emit diff_ready event if diffs produced
                            if ev.event_type == "tool_end" and ev.data.get("diff"):
                                yield MultiAgentEvent(
                                    event_type="diff_ready",
                                    role=AgentRole.CODER,
                                    data={"diff": ev.data.get("diff"), "file": ev.data.get("arguments", {}).get("file_path")},
                                )

            # ==========================================
            # STAGE 3: AUTOMATED VERIFICATION & HEALING
            # ==========================================
            yield MultiAgentEvent(
                event_type="pipeline_stage",
                role=AgentRole.ORCHESTRATOR,
                data={
                    "stage": "VERIFICATION",
                    "title": "Automated Quality, Security & Test Verification",
                },
            )

            async for event in self.verification_engine.verify_and_heal(memory, sandbox):
                yield self._map_agent_event(event)

            # ==========================================
            # STAGE 4: COMMIT VERIFIED SANDBOX CHANGES
            # ==========================================
            committed_files = sandbox.commit_to_workspace()
            yield MultiAgentEvent(
                event_type="pipeline_stage",
                role=AgentRole.ORCHESTRATOR,
                data={
                    "stage": "COMMIT",
                    "title": "Committed Verified Changes to Workspace",
                    "files_count": len(committed_files),
                    "committed_files": committed_files,
                },
            )

            # ==========================================
            # STAGE 5: FINAL SYNTHESIS BY ORCHESTRATOR
            # ==========================================
            yield MultiAgentEvent(
                event_type="pipeline_stage",
                role=AgentRole.ORCHESTRATOR,
                data={"stage": "SYNTHESIS", "title": "Orchestrator Final Synthesis"},
            )

            # Stream synthesis thought from Orchestrator LLM
            synthesis_prompt = f"""You are the Orchestrator Agent. Synthesize the final outcome of the multi-agent task.

USER GOAL:
{user_message}

EXECUTION CONTEXT:
- Architecture: {memory.architecture_summary}
- Tech Stack: {', '.join(memory.tech_stack)}
- Tasks Completed: {sum(1 for t in memory.tasks.values() if t.status == 'completed')}/{len(memory.tasks)}
- Files Created/Modified: {', '.join(memory.artifacts.keys()) or 'None'}
- Security Score: {memory.security_score}/100 ({len(memory.security_findings)} findings)
- Code Review Score: {memory.review_score}/100
- Test Suite: {memory.test_reports[-1].output_log if memory.test_reports else 'All checks passed'}

Provide a comprehensive, beautifully formatted Markdown response covering:
1. 🎯 **Solution Summary**: What was built/fixed.
2. 📁 **Key Files & Modules**: What each file does.
3. 🛡️ **Verification & Security Scorecard**: Summarize tests, security audit, and quality review.
4. 🚀 **How to Run / Test**: Clear terminal commands to test or run the output.
"""

            messages = [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_prompt},
            ]

            full_synthesis = ""
            async for chunk in self.ollama.chat_stream(
                model=self.model,
                messages=messages,
                options={"temperature": 0.2, "num_ctx": self.config.context_length},
            ):
                c = chunk.get("content", "")
                if c:
                    full_synthesis += c
                    yield MultiAgentEvent(
                        event_type="synthesis_chunk",
                        role=AgentRole.ORCHESTRATOR,
                        data={"chunk": c, "full": full_synthesis},
                    )

            if not full_synthesis:
                full_synthesis = memory.generate_markdown_summary()
                yield MultiAgentEvent(
                    event_type="synthesis_chunk",
                    role=AgentRole.ORCHESTRATOR,
                    data={"chunk": full_synthesis, "full": full_synthesis},
                )

            session.add_message(role="assistant", content=full_synthesis)

            # ==========================================
            # STAGE 6: COMPLETE
            # ==========================================
            yield MultiAgentEvent(
                event_type="done",
                role=AgentRole.ORCHESTRATOR,
                data={
                    "final_response": full_synthesis,
                    "summary": memory.get_context_snapshot(),
                    "committed_files": committed_files,
                },
            )

        except Exception as e:
            err_msg = f"Multi-Agent Execution Error: {str(e)}"
            session.add_message(role="assistant", content=err_msg)
            yield MultiAgentEvent(
                event_type="error",
                role=AgentRole.ORCHESTRATOR,
                data={"error": str(e)},
            )
            yield MultiAgentEvent(
                event_type="done",
                role=AgentRole.ORCHESTRATOR,
                data={"final_response": err_msg},
            )
        finally:
            sandbox.cleanup()

    def _map_agent_event(self, event: AgentExecutionEvent) -> MultiAgentEvent:
        """Translate specialized agent event into MultiAgentEvent."""
        mapping = {
            "start": "agent_start",
            "thought": "agent_thought",
            "tool_start": "agent_tool_start",
            "tool_end": "agent_tool_end",
            "completed": "agent_completed",
            "error": "error",
        }
        return MultiAgentEvent(
            event_type=mapping.get(event.event_type, "agent_thought"),
            role=event.agent_role,
            data=event.data,
        )
