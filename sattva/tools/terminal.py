"""
Terminal and Execution Tools for SATTVA AI AGENT.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from sattva.tools.base import BaseTool, ToolResult
from sattva.tools.file_ops import _resolve_path


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Execute a shell / terminal command in the workspace directory and capture its output (stdout and stderr)."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact shell command to execute.",
            },
            "cwd": {
                "type": "string",
                "description": "Optional working directory for the command (defaults to workspace root).",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Timeout in seconds before terminating process (default 60).",
                "default": 60,
            },
        },
        "required": ["command"],
    }

    async def execute(self, command: str, cwd: Optional[str] = None, timeout_seconds: int = 60, **kwargs) -> ToolResult:
        try:
            target_cwd = _resolve_path(self.workspace_path, cwd or ".")
            if not target_cwd.exists():
                return ToolResult(success=False, error=f"Working directory does not exist: '{cwd}'")

            # Determine shell
            is_win = sys.platform.startswith("win")
            shell_cmd = ["powershell", "-NoProfile", "-Command", command] if is_win else ["/bin/bash", "-c", command]

            proc = await asyncio.create_subprocess_exec(
                *shell_cmd,
                cwd=str(target_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=float(timeout_seconds),
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout_seconds} seconds: '{command}'",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            exit_code = proc.returncode

            # Format result
            output_parts = []
            if stdout:
                output_parts.append(f"STDOUT:\n{stdout}")
            if stderr:
                output_parts.append(f"STDERR:\n{stderr}")
            combined_output = "\n\n".join(output_parts) or "(No output)"

            # Cap output if excessively long
            if len(combined_output) > 20000:
                combined_output = combined_output[:20000] + "\n... [Output truncated at 20,000 characters]"

            is_success = exit_code == 0

            return ToolResult(
                success=is_success,
                data={
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                },
                error=None if is_success else f"Command exited with code {exit_code}\n{combined_output}",
                message=f"Command: `{command}` (Exit Code: {exit_code})\n\n```\n{combined_output}\n```",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to execute command '{command}': {str(e)}")


class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Run automated tests (pytest, npm test, etc.) in the project and return test report."
    parameters = {
        "type": "object",
        "properties": {
            "test_command": {
                "type": "string",
                "description": "Custom test command (e.g. 'pytest tests/test_core.py', 'npm test'). If omitted, auto-detects runner.",
            },
        },
    }

    async def execute(self, test_command: Optional[str] = None, **kwargs) -> ToolResult:
        workspace = Path(self.workspace_path)
        cmd = test_command

        if not cmd:
            if (workspace / "pytest.ini").exists() or (workspace / "tests").exists() or (workspace / "test").exists():
                cmd = "python -m pytest"
            elif (workspace / "package.json").exists():
                cmd = "npm test"
            elif (workspace / "Cargo.toml").exists():
                cmd = "cargo test"
            elif (workspace / "go.mod").exists():
                cmd = "go test ./..."
            else:
                cmd = "python -m unittest discover"

        runner = RunCommandTool(self.workspace_path)
        return await runner.execute(command=cmd, timeout_seconds=90)
