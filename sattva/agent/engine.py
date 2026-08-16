"""
Autonomous ReAct Agent Engine for SATTVA AI AGENT.
"""

import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from pydantic import BaseModel

from sattva.config import Config
from sattva.ollama_client import OllamaClient
from sattva.tools.base import ToolRegistry, ToolResult
from sattva.tools import create_default_registry
from sattva.agent.prompts import build_system_prompt
from sattva.agent.session import Session


class AgentEvent(BaseModel):
    event_type: str  # "start", "thought_chunk", "tool_start", "tool_end", "step", "done", "error"
    data: Dict[str, Any] = {}


def _extract_fallback_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Extract tool calls if model outputs them in Markdown/XML/JSON format in text."""
    tool_calls = []

    def _clean_json_str(s: str) -> str:
        s = s.strip()
        # Remove trailing commas before closing braces/brackets
        s = re.sub(r",\s*([\]}])", r"\1", s)
        return s

    # 1. Match ```tool_call ... ``` or ```json:tool_call ... ``` or ```tool ... ``` or ```json ... ```
    pattern_block = r"```(?:tool_call|json:tool_call|tool|json)?\s*([\s\S]*?)```"
    for match in re.finditer(pattern_block, text):
        raw = match.group(1).strip()
        if not raw.startswith("{"):
            continue
        try:
            parsed = json.loads(_clean_json_str(raw))
            if isinstance(parsed, dict):
                # Format A: {"name": "...", "arguments": {...}}
                name = parsed.get("name") or parsed.get("tool") or parsed.get("function", {}).get("name")
                args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or parsed.get("function", {}).get("arguments") or {}
                if name:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    tool_calls.append({"function": {"name": str(name), "arguments": args if isinstance(args, dict) else {}}})
        except Exception:
            pass

    # 2. Match <tool_call>...</tool_call>
    pattern_xml = r"<tool_call>\s*([\s\S]*?)\s*</tool_call>"
    for match in re.finditer(pattern_xml, text):
        raw = match.group(1).strip()
        try:
            parsed = json.loads(_clean_json_str(raw))
            if isinstance(parsed, dict):
                name = parsed.get("name") or parsed.get("tool") or parsed.get("function", {}).get("name")
                args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or parsed.get("function", {}).get("arguments") or {}
                if name:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    tool_calls.append({"function": {"name": str(name), "arguments": args if isinstance(args, dict) else {}}})
        except Exception:
            pass

    return tool_calls


class SattvaAgent:
    def __init__(
        self,
        config: Optional[Config] = None,
        workspace_path: Optional[str] = None,
        model: Optional[str] = None,
        tools_registry: Optional[ToolRegistry] = None,
    ):
        self.config = config or Config(workspace_path)
        self.workspace_path = str(self.config.workspace_path)
        self.model = model or self.config.default_model
        self.ollama = OllamaClient(base_url=self.config.ollama_url)
        self.tools = tools_registry or create_default_registry(self.workspace_path)

    def set_model(self, model_name: str) -> None:
        self.model = model_name

    def set_workspace(self, workspace_path: str) -> None:
        self.workspace_path = workspace_path
        self.tools = create_default_registry(self.workspace_path)

    async def run(
        self,
        user_message: str,
        session: Optional[Session] = None,
        mode: str = "agent",  # "agent" (full tools) or "ask" (fast chat)
        max_iterations: Optional[int] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute an autonomous multi-step reasoning and tool-calling cycle.
        Yields streaming AgentEvent objects.
        """
        max_iter = max_iterations or self.config.max_iterations

        if session is None:
            session = Session(model=self.model, workspace_path=self.workspace_path)

        session.add_message(role="user", content=user_message)
        yield AgentEvent(event_type="start", data={"model": self.model, "mode": mode, "workspace": self.workspace_path})

        # Build system message
        tools_doc = self.tools.get_tools_prompt_documentation() if mode == "agent" else ""
        system_prompt = build_system_prompt(
            workspace_path=self.workspace_path,
            tools_doc=tools_doc,
            include_xml_fallback=(mode == "agent"),
        )

        schemas = self.tools.get_all_schemas() if mode == "agent" else None

        # Prepare messages history
        working_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        # Include prior conversation turns from session (last 15 messages for context budget)
        for msg in session.messages[-15:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                working_messages.append({"role": role, "content": content})

        iteration = 0
        final_answer = ""

        options = {
            "temperature": self.config.temperature,
            "num_ctx": self.config.context_length,
        }

        while iteration < max_iter:
            iteration += 1
            step_thought = ""
            active_tool_calls: List[Dict[str, Any]] = []

            yield AgentEvent(
                event_type="step",
                data={"iteration": iteration, "max_iterations": max_iter},
            )

            # Stream from Ollama
            async for chunk in self.ollama.chat_stream(
                model=self.model,
                messages=working_messages,
                tools=schemas if mode == "agent" else None,
                options=options,
            ):
                if chunk.get("error"):
                    err_msg = chunk.get("content", "Unknown Ollama error")
                    yield AgentEvent(event_type="error", data={"message": err_msg})
                    session.add_message(role="assistant", content=err_msg)
                    yield AgentEvent(event_type="done", data={"final_response": err_msg, "iterations": iteration})
                    return

                chunk_content = chunk.get("content", "")
                if chunk_content:
                    step_thought += chunk_content
                    yield AgentEvent(event_type="thought_chunk", data={"chunk": chunk_content, "full": step_thought})

                calls = chunk.get("tool_calls", [])
                if calls:
                    active_tool_calls.extend(calls)

            # Check if any tool calls were returned natively
            if not active_tool_calls and mode == "agent":
                # Fallback: check if model emitted tool call in text
                fallback_calls = _extract_fallback_tool_calls(step_thought)
                if fallback_calls:
                    active_tool_calls.extend(fallback_calls)

            # If no tool calls, model is finished!
            if not active_tool_calls or mode == "ask":
                final_answer = step_thought
                session.add_message(role="assistant", content=final_answer)
                yield AgentEvent(
                    event_type="done",
                    data={
                        "final_response": final_answer,
                        "iterations": iteration,
                    },
                )
                return

            # Append assistant step to working history
            working_messages.append({
                "role": "assistant",
                "content": step_thought,
                "tool_calls": active_tool_calls,
            })

            # Execute tool calls
            for t_call in active_tool_calls:
                func = t_call.get("function", {})
                tool_name = func.get("name", "")
                tool_args = func.get("arguments", {})

                # Ensure args is dict
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except Exception:
                        tool_args = {}

                yield AgentEvent(
                    event_type="tool_start",
                    data={"tool": tool_name, "arguments": tool_args, "iteration": iteration},
                )

                # Execute
                result: ToolResult = await self.tools.execute(tool_name, tool_args)

                yield AgentEvent(
                    event_type="tool_end",
                    data={
                        "tool": tool_name,
                        "arguments": tool_args,
                        "success": result.success,
                        "result": result.to_dict(),
                        "message": str(result),
                        "iteration": iteration,
                    },
                )

                # Feed result back to model messages
                working_messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": str(result),
                })

        # Reached max iterations
        timeout_msg = f"Task completed or reached maximum iteration limit ({max_iter} steps)."
        session.add_message(role="assistant", content=timeout_msg)
        yield AgentEvent(event_type="done", data={"final_response": timeout_msg, "iterations": iteration})
