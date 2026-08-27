"""
Isolated Workspace Sandbox for SATTVA AI Multi-Agent Mode.
Allows Coder and other agents to stage, test, and verify code modifications in an isolated environment
before committing to the main workspace.
"""

import os
import shutil
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import uuid

from sattva.tools.base import BaseTool, ToolResult, ToolRegistry
from sattva.tools.file_ops import (
    CreateFileTool,
    CreateFolderTool,
    ReadFileTool,
    DeleteFileOrFolderTool,
    ListDirectoryTool,
)
from sattva.tools.code_edit import (
    EditFileTool,
    InsertCodeTool,
    _generate_diff,
)
from sattva.tools.scanner import ScanCodebaseTool
from sattva.tools.search import SearchCodeTool, FindFilesTool
from sattva.tools.terminal import RunCommandTool, RunTestsTool


class WorkspaceSandbox:
    """
    Manages an isolated workspace sandbox overlay for an agent or task execution.
    Staged changes remain in the sandbox until verification passes and they are committed.
    """

    def __init__(self, base_workspace: str, sandbox_id: Optional[str] = None):
        self.base_workspace = Path(base_workspace).resolve()
        self.sandbox_id = sandbox_id or f"sandbox_{str(uuid.uuid4())[:8]}"
        self.sandbox_dir = self.base_workspace / ".sattva" / "sandboxes" / self.sandbox_id
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        self.staged_files: Dict[str, str] = {}  # rel_path -> "created" | "modified" | "deleted"
        self.staged_diffs: Dict[str, str] = {}  # rel_path -> unified_diff

    def _resolve_sandbox_path(self, rel_path: str) -> Path:
        """Resolve a relative path inside the sandbox directory."""
        clean = Path(rel_path).as_posix().lstrip("/")
        return self.sandbox_dir / clean

    def _resolve_base_path(self, rel_path: str) -> Path:
        """Resolve a relative path inside the base workspace."""
        clean = Path(rel_path).as_posix().lstrip("/")
        return self.base_workspace / clean

    def stage_file_create(self, rel_path: str, content: str) -> Dict[str, Any]:
        """Stage a new file creation inside the sandbox."""
        clean_rel = Path(rel_path).as_posix().lstrip("/")
        target = self._resolve_sandbox_path(clean_rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        base_file = self._resolve_base_path(clean_rel)
        action = "modified" if base_file.exists() else "created"
        old_content = base_file.read_text(encoding="utf-8", errors="replace") if base_file.exists() else ""
        diff = _generate_diff(old_content, content, clean_rel)

        self.staged_files[clean_rel] = action
        self.staged_diffs[clean_rel] = diff

        return {
            "path": clean_rel,
            "action": action,
            "diff": diff,
            "bytes": len(content.encode("utf-8")),
        }

    def stage_file_edit(self, rel_path: str, target_content: str, replacement_content: str) -> Dict[str, Any]:
        """Stage an edit on an existing file inside the sandbox."""
        clean_rel = Path(rel_path).as_posix().lstrip("/")
        sandboxed_target = self._resolve_sandbox_path(clean_rel)
        base_target = self._resolve_base_path(clean_rel)

        # Source file content (from sandbox if already staged, otherwise from base)
        if sandboxed_target.exists():
            original = sandboxed_target.read_text(encoding="utf-8", errors="replace")
        elif base_target.exists():
            original = base_target.read_text(encoding="utf-8", errors="replace")
        else:
            raise FileNotFoundError(f"Cannot edit non-existent file '{clean_rel}'")

        normalized_orig = original.replace("\r\n", "\n")
        normalized_target = target_content.replace("\r\n", "\n")
        normalized_repl = replacement_content.replace("\r\n", "\n")

        if normalized_target not in normalized_orig:
            # Try whitespace stripped line-by-line fallback
            target_lines = [l.strip() for l in normalized_target.strip().split("\n")]
            orig_lines = normalized_orig.split("\n")
            found = False
            for i in range(len(orig_lines) - len(target_lines) + 1):
                window = [orig_lines[i + j].strip() for j in range(len(target_lines))]
                if window == target_lines:
                    # Match found
                    new_lines = orig_lines[:i] + normalized_repl.split("\n") + orig_lines[i + len(target_lines):]
                    new_content = "\n".join(new_lines)
                    found = True
                    break
            if not found:
                raise ValueError(f"Target content not found in '{clean_rel}'")
        else:
            new_content = normalized_orig.replace(normalized_target, normalized_repl, 1)

        sandboxed_target.parent.mkdir(parents=True, exist_ok=True)
        sandboxed_target.write_text(new_content, encoding="utf-8")

        base_content = base_target.read_text(encoding="utf-8", errors="replace") if base_target.exists() else ""
        diff = _generate_diff(base_content, new_content, clean_rel)

        self.staged_files[clean_rel] = "modified"
        self.staged_diffs[clean_rel] = diff

        return {
            "path": clean_rel,
            "action": "modified",
            "diff": diff,
        }

    def read_file(self, rel_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Read file content, prioritizing sandboxed staged version over base workspace."""
        clean_rel = Path(rel_path).as_posix().lstrip("/")
        sandboxed_target = self._resolve_sandbox_path(clean_rel)
        base_target = self._resolve_base_path(clean_rel)

        if sandboxed_target.exists():
            content = sandboxed_target.read_text(encoding="utf-8", errors="replace")
        elif base_target.exists():
            content = base_target.read_text(encoding="utf-8", errors="replace")
        else:
            raise FileNotFoundError(f"File '{clean_rel}' not found.")

        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            s = max(0, (start_line - 1)) if start_line else 0
            e = min(len(lines), end_line) if end_line else len(lines)
            return "\n".join(lines[s:e])
        return content

    def stage_file_delete(self, rel_path: str) -> None:
        """Stage file deletion."""
        clean_rel = Path(rel_path).as_posix().lstrip("/")
        sandboxed_target = self._resolve_sandbox_path(clean_rel)
        if sandboxed_target.exists():
            sandboxed_target.unlink()
        self.staged_files[clean_rel] = "deleted"
        self.staged_diffs[clean_rel] = f"--- a/{clean_rel}\n+++ /dev/null\n@@ -1 +0,0 @@\n-[DELETED]"

    def commit_to_workspace(self) -> List[Dict[str, Any]]:
        """Commit and merge all staged sandbox modifications into the real base workspace."""
        committed = []
        for rel_path, action in self.staged_files.items():
            base_target = self._resolve_base_path(rel_path)
            sandboxed_target = self._resolve_sandbox_path(rel_path)

            if action in ["created", "modified"]:
                if sandboxed_target.exists():
                    base_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sandboxed_target, base_target)
                    committed.append({
                        "path": rel_path,
                        "action": action,
                        "diff": self.staged_diffs.get(rel_path),
                    })
            elif action == "deleted":
                if base_target.exists():
                    if base_target.is_dir():
                        shutil.rmtree(base_target, ignore_errors=True)
                    else:
                        base_target.unlink(missing_ok=True)
                    committed.append({
                        "path": rel_path,
                        "action": "deleted",
                    })

        # Cleanup sandbox directory after commit
        self.cleanup()
        return committed

    def rollback(self) -> None:
        """Discard all staged changes in the sandbox."""
        self.staged_files.clear()
        self.staged_diffs.clear()
        self.cleanup()

    def cleanup(self) -> None:
        """Delete temporary sandbox folder."""
        if self.sandbox_dir.exists():
            try:
                shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            except Exception:
                pass

    def create_sandboxed_registry(self) -> ToolRegistry:
        """Create a ToolRegistry wired to operate inside this isolated sandbox overlay."""
        sandbox = self

        class SandboxedCreateFileTool(BaseTool):
            name = "create_file"
            description = "Create or overwrite a file inside the isolated sandbox."
            parameters = {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file"},
                    "content": {"type": "string", "description": "Full file content"},
                    "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": True},
                },
                "required": ["file_path", "content"],
            }

            async def execute(self, file_path: str, content: str, overwrite: bool = True) -> ToolResult:
                try:
                    res = sandbox.stage_file_create(file_path, content)
                    return ToolResult(
                        success=True,
                        data=res,
                        message=f"Staged file '{file_path}' ({res['action']}) in sandbox.",
                    )
                except Exception as e:
                    return ToolResult(success=False, error=str(e))

        class SandboxedEditFileTool(BaseTool):
            name = "edit_file"
            description = "Surgically edit a file in the isolated sandbox."
            parameters = {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file"},
                    "target_content": {"type": "string", "description": "Exact text chunk to replace"},
                    "replacement_content": {"type": "string", "description": "Replacement text"},
                },
                "required": ["file_path", "target_content", "replacement_content"],
            }

            async def execute(self, file_path: str, target_content: str, replacement_content: str) -> ToolResult:
                try:
                    res = sandbox.stage_file_edit(file_path, target_content, replacement_content)
                    return ToolResult(
                        success=True,
                        data=res,
                        message=f"Staged edit for '{file_path}' in sandbox.",
                    )
                except Exception as e:
                    return ToolResult(success=False, error=str(e))

        class SandboxedReadFileTool(BaseTool):
            name = "read_file"
            description = "Read a file from sandbox (or workspace if not staged)."
            parameters = {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file"},
                    "start_line": {"type": "integer", "description": "Start line (1-indexed)"},
                    "end_line": {"type": "integer", "description": "End line"},
                },
                "required": ["file_path"],
            }

            async def execute(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
                try:
                    content = sandbox.read_file(file_path, start_line, end_line)
                    return ToolResult(
                        success=True,
                        data={"content": content, "path": file_path},
                        message=content,
                    )
                except Exception as e:
                    return ToolResult(success=False, error=str(e))

        registry = ToolRegistry(str(self.base_workspace))
        registry.register(SandboxedCreateFileTool)
        registry.register(SandboxedEditFileTool)
        registry.register(SandboxedReadFileTool)
        registry.register(CreateFolderTool)
        registry.register(DeleteFileOrFolderTool)
        registry.register(ListDirectoryTool)
        registry.register(InsertCodeTool)
        registry.register(ScanCodebaseTool)
        registry.register(SearchCodeTool)
        registry.register(FindFilesTool)
        registry.register(RunCommandTool)
        registry.register(RunTestsTool)

        return registry
